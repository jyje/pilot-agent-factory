"""SDK ↔ agent version compatibility checks.

Rule (semver):
- major versions must match.
- while the SDK is 0.x, minor versions must also match — 0.x minors are
  treated as breaking, per semver convention.
"""

from __future__ import annotations

from .contract import SDK_VERSION, AgentManifest


class IncompatibleAgentError(Exception):
    """Raised when an agent targets an incompatible SDK version."""


def _parse(version: str) -> tuple[int, int, int]:
    try:
        major, minor, patch = (int(p) for p in version.split("."))
    except ValueError as e:
        raise IncompatibleAgentError(f"invalid semver string: {version!r}") from e
    return major, minor, patch


def check_compat(manifest: AgentManifest, sdk_version: str = SDK_VERSION) -> None:
    """Raise IncompatibleAgentError if `manifest` cannot run on this SDK."""
    agent_v = _parse(manifest.sdk_version)
    sdk_v = _parse(sdk_version)

    compatible = agent_v[0] == sdk_v[0] and (sdk_v[0] != 0 or agent_v[1] == sdk_v[1])
    if not compatible:
        raise IncompatibleAgentError(
            f"agent {manifest.name!r} targets SDK {manifest.sdk_version}, "
            f"but installed SDK is {sdk_version}"
        )
