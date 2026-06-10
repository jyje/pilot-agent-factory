# Architecture

> [한국어](01-architecture-ko.md)

## The 4-layer pattern

```
1. Contract     agent-factory-sdk: AgentManifest + SubAgent protocol
2. Packaging    each agent = a pip package with an entry point
3. Loading      AgentRegistry: entry points (A) + drop-in files (B)
4. Assembly     supervisor builds nodes from manifests   ← Phase 4, not yet here
```

This repository implements phases 1–3.

## Layer 1 — Contract (`agent_factory_sdk.contract`)

```python
class AgentManifest(BaseModel):
    name: str             # unique id, kebab/snake case
    version: str          # agent semver
    sdk_version: str      # SDK version the agent was built against
    description: str
    capabilities: list[str]      # routing hints for the future supervisor
    input_schema: dict           # JSON Schema, defaults to messages-in
    output_schema: dict          # JSON Schema, defaults to messages-out

@runtime_checkable
class SubAgent(Protocol):
    manifest: AgentManifest
    def build(self, config: dict | None = None) -> Runnable: ...
```

Key decisions:

- **`build()` is a factory.** Graphs are never compiled at import time. This lets the host inject an LLM (`config["llm"]`), and lets the test harness run every agent against a `ScriptedChatModel` with zero network access. Agents obtain their model via `resolve_llm(config)` — injected client first, env-built `ChatAnthropic` otherwise.
- **`SubAgent` is a `Protocol`, not a base class.** Agent packages depend on the SDK only for `AgentManifest` and helpers; they never inherit SDK internals, which keeps the compatibility surface small.
- **Manifest lives in code, not in a separate `agent.yaml`.** A yaml manifest was considered (and is common in plugin systems), but a second source of truth drifts from the code. Pydantic validation at import time gives the same guarantees with one artifact. If a non-Python registry ever needs the metadata, `manifest.model_dump_json()` exports it.
- **State contract is messages-in/messages-out by default.** Agents with richer state (see `agent-summarizer`'s `summary` channel) declare it in `output_schema`; the Phase 4 supervisor will use these schemas to generate state-mapping adapters so sub-agents stay decoupled from supervisor state.

## Compatibility gate (`compat.py`)

Every load runs `check_compat(manifest)`:

- major versions must match;
- while the SDK is `0.x`, the minor must match too (semver treats `0.x` minors as breaking).

Incompatible agents become load errors, not crashes.

## Layer 3 — Loader (`agent_factory_sdk.loader`)

```
AgentRegistry.discover(dropin_dir=...)
 ├── Mode A: importlib.metadata.entry_points(group="agent_factory.agents")
 └── Mode B: importlib spec-from-file for dropins/*.py, module-level AGENT
```

| | Mode A (entry points) | Mode B (drop-ins) |
|--|----------------------|-------------------|
| Unit | pip package | single `.py` file |
| Dependency management | pip/uv resolves | host venv only |
| Use case | default, CI-tested releases | hot-swap on mounted volumes, experiments |
| Discovery | `[project.entry-points."agent_factory.agents"]` | directory scan, `AGENT` attribute |

**Failure isolation** is the loader's core invariant: each entry point / file is loaded in its own `try`, and failures are recorded as `LoadError(source, error)` in the `LoadReport` instead of raising. Name collisions keep the first agent (installed wins over drop-in) and record the duplicate as an error. The host stays up with whatever loaded; `main.py list` prints both sections.

For Kubernetes, Mode B's recommended shape is still *wheels installed to a PVC* (`pip install --target`) + `sys.path` extension, not raw files — raw drop-ins are for local development and demos. True in-process hot reload is intentionally out of scope (module-cache invalidation is not worth it; `rollout restart` is simpler and safer).

## Test harness (`agent_factory_sdk.testing`)

- `assert_agent_valid(agent)` — the one-call CI gate: protocol shape, manifest validity, compat, and `build()` returning a `Runnable` under an injected fake model.
- `ScriptedChatModel` — replays a fixed list of responses, implements `bind_tools()` as a no-op, so even the calculator's ReAct loop runs end-to-end in tests without an endpoint.

## Known limits / escape hatch

All agents share one process and one dependency resolution. The SDK pins a band of `langgraph`/`langchain-core`; an agent whose dependencies cannot co-resolve should be split into its own service and called remotely (A2A) — that escape hatch is a Phase 5 concern and intentionally absent here.
