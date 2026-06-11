# Phase 5 — Deep Agent Orchestration

> [한국어](04-phase5-plan-ko.md) · Status: **implemented**
>
> Pivot note: Phase 5 was originally scoped as a zip/tar/git import pipeline.
> That work moved to **Phase 6 (planned)** — see the bottom of this doc.
> Phase 5 instead puts a [deep agent](https://docs.langchain.com/oss/python/deepagents)
> at the top of the stack, adds structure visibility, and makes conversations
> multi-turn.

## What changed

```
Phase 4                              Phase 5
─────────                            ─────────
hand-rolled router (route tool)  →   deepagents on top (task tool, todos, summarization)
single-shot conversations        →   sessions via checkpointer (thread_id)
structure only in code           →   Mermaid graph views in CLI and web
```

`build_deep_supervisor(registry, config, checkpointer)` in
`agent_factory_sdk.deep` assembles the same runtime-loaded agents — unchanged,
as `CompiledSubAgent`s — under `create_deep_agent`. The Phase 4
`build_supervisor` remains available (CLI `--simple`, `SUPERVISOR_MODE=simple`).

## 1 · Deep agent on top, filesystem disconnected

- Registry agents become deepagents `CompiledSubAgent`s: manifest
  `description` + `capabilities` become the `task` tool's delegation hints —
  the same fields the Phase 4 router consumed.
- A process-wide `HarnessProfile` (registered for the `anthropic` provider,
  which includes LM Studio behind the Anthropic-compatible endpoint) hides the
  entire filesystem/sandbox tool surface (`ls`, `read_file`, `write_file`,
  `edit_file`, `glob`, `grep`, `execute`). deepagents ≥0.6.8 treats
  `FilesystemMiddleware` as required scaffolding, so disconnection is per-tool
  rather than middleware removal — functionally identical: the model can never
  see or call a filesystem tool.
- The auto-added `general-purpose` subagent is disabled, so **the only path to
  real work is the registry's sub-agents**.

## 2 · Structure visibility

| Surface | Command / endpoint | Shows |
|---|---|---|
| CLI | `uv run python main.py graph` | platform overview: supervisor + every agent's real internal graph as Mermaid subgraphs |
| CLI | `main.py graph <agent>` / `--top` | one agent's compiled graph / the deep agent's own runtime graph |
| API | `GET /api/graph`, `/api/graph/top`, `/api/graph/{name}` | same three scopes as JSON `{scope, mermaid}` |
| Web | header **Structure** button · click any agent card | Mermaid rendered client-side in a dialog |

The overview (`render_platform_mermaid`) is generated from each agent's
*compiled* graph topology, not hand-drawn — an imported agent shows up with
its actual nodes and edges, no drawing code required.

![Platform structure dialog](assets/scenario-4-structure.png)

## 3 · Multi-turn sessions

Both supervisors accept a LangGraph `checkpointer`; conversations are keyed by
`thread_id`:

- **API**: `POST /api/chat` takes `session_id`; the backend holds a
  `MemorySaver` and streams only what grows past the thread's existing history.
- **Web**: a session chip + **New session** button; the page keeps one session
  id per conversation.
- **CLI**: `main.py chat` without a prompt opens a REPL on a single thread.

Verified live on LM Studio: turn 1 "My name is Jay" → turn 2 "What is my
name?" → *"Jay"*, with the model citing the previous turn; then a `task`
delegation to calculator in the same session.

![Multi-turn memory](assets/scenario-5-multiturn.png)
![Deep delegation via task tool](assets/scenario-6-deep-delegation.png)

## Known limits

- `MemorySaver` is in-process: sessions die with the server. A durable
  checkpointer (SQLite/Postgres) is a drop-in swap when needed.
- Small local models are flaky as deep-agent drivers: they sometimes emit
  empty replies (`[]`) or skip delegation; re-prompting works, and every path
  degrades safely. Claude-class models do not exhibit this.
- The deep agent's own runtime graph (`graph --top`) shows the middleware
  loop, which is faithful but less readable than the platform overview — the
  overview is the intended default.

## Phase 6 (planned) — distribution & import

The previous Phase 5 plan, deferred intact: import agents from zip/tar
archives and git repos following the package convention
(`pyproject.toml` with one `agent_factory.agents` entry point), with a
validation gate (dependency band, subprocess isolation), versioned install
dirs, `agents.lock` pinning, and a `jyje/pilot-agent-template` example repo.
The graph overview from this phase doubles as the import verification view:
a freshly imported agent should appear there immediately.
