"""Phase 3 — runtime loading of sub-agent packages.

Two modes:
- Mode A `load_installed_agents()`: discover pip-installed packages via the
  `agent_factory.agents` entry-point group. Default mode.
- Mode B `load_dropin_agents(dir)`: import `*.py` files from a directory and
  read their module-level `AGENT` object. Intended for mounted volumes
  (PVC/ConfigMap) where rebuilding the image is not an option.

Failure isolation: one broken agent must never prevent the host from booting,
so loaders collect per-source errors instead of raising. Only the registry's
`get()` raises, and only for lookups of agents that failed or don't exist.
"""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass, field
from importlib.metadata import entry_points
from pathlib import Path

from .compat import check_compat
from .contract import AgentManifest, SubAgent

ENTRY_POINT_GROUP = "agent_factory.agents"
DROPIN_ATTR = "AGENT"
_DROPIN_MODULE_PREFIX = "agent_factory_dropin_"


@dataclass
class LoadError:
    source: str  # entry point name or file path
    error: str


@dataclass
class LoadReport:
    agents: dict[str, SubAgent] = field(default_factory=dict)
    errors: list[LoadError] = field(default_factory=list)

    def merge(self, other: "LoadReport") -> "LoadReport":
        for name, agent in other.agents.items():
            if name in self.agents:
                self.errors.append(
                    LoadError(source=name, error=f"duplicate agent name {name!r} — keeping first")
                )
            else:
                self.agents[name] = agent
        self.errors.extend(other.errors)
        return self


def _validate(obj: object, source: str) -> SubAgent:
    """Coerce an entry-point/dropin object into a verified SubAgent instance."""
    if isinstance(obj, type):  # a class was exported — instantiate it
        obj = obj()
    if not isinstance(obj, SubAgent):
        raise TypeError(f"{source}: object does not satisfy the SubAgent protocol")
    manifest = obj.manifest
    if not isinstance(manifest, AgentManifest):
        # Allow duck-typed manifests (e.g. loaded from yaml) by re-validating.
        obj.manifest = AgentManifest.model_validate(manifest)
    check_compat(obj.manifest)
    return obj


def load_installed_agents() -> LoadReport:
    """Mode A: discover agents from installed packages' entry points."""
    report = LoadReport()
    for ep in entry_points(group=ENTRY_POINT_GROUP):
        try:
            agent = _validate(ep.load(), source=f"entry point {ep.name!r}")
            report.agents[agent.manifest.name] = agent
        except Exception as e:  # noqa: BLE001 — isolation: record and continue
            report.errors.append(LoadError(source=ep.name, error=f"{type(e).__name__}: {e}"))
    return report


def load_dropin_agents(directory: str | Path) -> LoadReport:
    """Mode B: import `*.py` files from `directory`, expecting module-level AGENT."""
    report = LoadReport()
    directory = Path(directory)
    if not directory.is_dir():
        return report

    for path in sorted(directory.glob("*.py")):
        if path.name.startswith("_"):
            continue
        try:
            agent = _validate(_import_dropin(path), source=str(path))
            report.agents[agent.manifest.name] = agent
        except Exception as e:  # noqa: BLE001 — isolation: record and continue
            report.errors.append(LoadError(source=str(path), error=f"{type(e).__name__}: {e}"))
    return report


def _import_dropin(path: Path) -> object:
    module_name = _DROPIN_MODULE_PREFIX + path.stem
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot create import spec for {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    if not hasattr(module, DROPIN_ATTR):
        raise AttributeError(f"{path.name} defines no module-level {DROPIN_ATTR}")
    return getattr(module, DROPIN_ATTR)


class AgentRegistry:
    """Aggregates both load modes and answers name → agent lookups."""

    def __init__(self) -> None:
        self.report = LoadReport()

    def discover(self, dropin_dir: str | Path | None = None) -> "AgentRegistry":
        self.report = load_installed_agents()
        if dropin_dir is not None:
            self.report.merge(load_dropin_agents(dropin_dir))
        return self

    @property
    def agents(self) -> dict[str, SubAgent]:
        return self.report.agents

    @property
    def errors(self) -> list[LoadError]:
        return self.report.errors

    def manifests(self) -> list[AgentManifest]:
        return [a.manifest for a in self.agents.values()]

    def get(self, name: str) -> SubAgent:
        try:
            return self.agents[name]
        except KeyError:
            known = ", ".join(sorted(self.agents)) or "(none)"
            raise KeyError(f"unknown agent {name!r} — loaded agents: {known}") from None
