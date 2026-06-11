<div align="center">

# jyje/pilot-agent-factory

🏭 Pilot project for standardized, runtime-loadable LangGraph sub-agent packages

[![GitHub Repo stars](https://img.shields.io/github/stars/jyje/pilot-agent-factory?style=social)](https://github.com/jyje/pilot-agent-factory)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![LangGraph](https://img.shields.io/badge/LangGraph-StateGraph-blue)](https://github.com/langchain-ai/langgraph)
[![Python](https://img.shields.io/badge/Python-3.14-blue)](https://www.python.org)

[English](README.md) · [한국어](README-ko.md) · [Docs](docs/README.md)

---

**Found this useful? Please give it a ⭐ — it helps others find it.**

</div>

## Overview

A pattern for developing LangGraph sub-agents as **standardized plugin packages** and loading them at runtime — without the host knowing them at build time.

```
Contract (SDK) → Packaging (entry points) → Runtime loading → Supervisor → Deep orchestration
   Phase 1           Phase 2                   Phase 3         Phase 4       Phase 5
                                                     Phase 6 (planned): zip/tar/git import
```

Every sub-agent is a pip package that exposes a `manifest` (metadata + routing hints) and a `build()` factory returning a compiled `StateGraph`. The host discovers agents through two modes:

- **Mode A — entry points**: pip-installed packages registered under the `agent_factory.agents` group (default)
- **Mode B — drop-ins**: plain `.py` files imported from a directory at runtime (the local stand-in for a mounted PVC/ConfigMap)

One broken agent never blocks the host: load failures are isolated and reported per source. A **deep agent** sits on top (Phase 5) — it plans, delegates to the loaded agents through the `task` tool (filesystem disconnected, sub-agent routing only), and keeps **multi-turn sessions** via a checkpointer. The platform's structure is visible as **Mermaid graph views** in both CLI and web.

```
        host (main.py chat · app/backend · web app)
                         │ discover
            ┌────────────┼─────────────┐
            ▼            ▼             ▼
     entry points   entry points    dropins/*.py
    agent-chitchat  agent-calculator  agent_pirate.py
    agent-summarizer        │
            └────────────┬──┘
                         ▼
      deep supervisor (task tool) over CompiledSubAgents
        · sessions: thread_id × checkpointer
        · structure: /api/graph · main.py graph
```

![Agent Factory web app](docs/assets/webapp-calculator.png)

## Demo — live scenarios on a local model

All captured against LM Studio (`google/gemma-4-e4b`) through the web console. The route chips between messages are the supervisor's actual decisions (`route_trace`), streamed over SSE.

### 1 · Cross-agent collaboration (Korean math)

*"55 더하기 11은 뭔가요?"* — the supervisor routes to **calculator** (runs the `add` tool), then hands off to **chitchat**, which answers naturally in Korean ("55에 11을 더하면 66이에요 😊") before FINISH. Two specialized agents cooperating on one request, with no orchestration code specific to either.

![Scenario 1 — calculator + chitchat](docs/assets/scenario-1-calculator-ko.png)

### 2 · Custom state channels (summarizer + artifacts)

A summarize request routes to **summarizer**, whose two-node pipeline returns bullet points as the reply *and* lifts its `summary` state channel into the supervisor's `artifacts` — visible as the 📦 card, exactly as declared in the agent's `output_schema`.

![Scenario 2 — summarizer artifacts](docs/assets/scenario-2-summarizer.png)

### 3 · Drop-in agent routing (pirate)

The **pirate** agent was never pip-installed — it's a single file in `dropins/`. The router still finds and picks it from its manifest capabilities. This run also shows the router's degradation path on a weak local model: it re-consults pirate before the routing-history hint pushes it to FINISH.

![Scenario 3 — pirate drop-in](docs/assets/scenario-3-pirate.png)

### 4 · Platform structure view (Phase 5)

The header's **Structure** button (or `main.py graph`) renders the live topology: the deep supervisor connected by `task` edges to every loaded agent's *actual* compiled graph — calculator's ReAct loop, summarizer's two-node pipeline. Generated from the registry, so an imported agent appears with zero drawing code.

![Scenario 4 — structure dialog](docs/assets/scenario-4-structure.png)

### 5 · Multi-turn session memory (Phase 5)

Turn 1: *"My name is Jay."* Turn 2: *"What is my name?"* → **"Jay"**, the model citing the previous turn — conversation state lives server-side in a checkpointer keyed by the session chip's `thread_id`. Then, in the same session, the deep agent delegates a calculation via the `task` tool.

![Scenario 5 — multi-turn memory](docs/assets/scenario-5-multiturn.png)
![Scenario 6 — deep delegation](docs/assets/scenario-6-deep-delegation.png)

### 6 · Token streaming with per-agent attribution

Every LLM token streams live over SSE, attributed to its producer: each bubble carries an **agent badge**, the footer shows **who is working right now**, and tool chips flip Running → Completed. Model thinking streams inside an **open Reasoning fold** ("Thinking…", first capture) that **auto-collapses into "Thought for N seconds"** when the stream ends (second capture).

![Scenario 7 — live streaming](docs/assets/scenario-7-streaming-live.png)
![Scenario 8 — reasoning fold](docs/assets/scenario-8-reasoning-fold.png)

## What's inside

| Component | Role |
|---------|------|
| `src/packages/agent-factory-sdk` | Contract (`AgentManifest`, `SubAgent`), semver compat gate, loader/registry, supervisor assembly, **deep orchestration + graph rendering**, test harness |
| `src/packages/agent-chitchat` | Example 1 — single-node conversational graph |
| `src/packages/agent-calculator` | Example 2 — ReAct tool loop (add/subtract/multiply/divide) |
| `src/packages/agent-summarizer` | Example 3 — two-node pipeline with a custom `summary` state channel |
| `src/dropins/agent_pirate.py` | Mode B demo — loaded from a file, never pip-installed |
| `app/backend` | FastAPI consumer of the platform — `/api/agents`, `/api/chat` (SSE) |
| `app/frontend` | Next.js 16 + AI Elements + shadcn/ui supervisor console |

## Quick Start

Runs fully local against [LM Studio](https://lmstudio.ai)'s Anthropic-compatible endpoint — no API key needed.

```bash
git clone https://github.com/jyje/pilot-agent-factory.git
cd pilot-agent-factory/src
cp .env.sample .env   # defaults to LM Studio at http://127.0.0.1:1234

uv sync --dev

# verify: env, endpoint, agent discovery, inference
uv run python doctor.py

# list discovered agents (3 installed + 1 drop-in)
uv run python main.py list

# run one agent directly, or let the deep supervisor delegate
uv run python main.py run calculator "What is (17 + 25) * 3?"
uv run python main.py chat "What is (17 + 25) * 3?"
uv run python main.py chat            # multi-turn REPL (session memory)
uv run python main.py graph           # Mermaid platform structure

# LLM-free test suite (contract + loader + agents + supervisors)
uv run pytest
```

### Web app (supervisor console)

```bash
# terminal 1 — backend
cd app/backend && uv sync
uv run fastapi dev src/agent_factory_backend/server.py

# terminal 2 — frontend
cd app/frontend && pnpm install
pnpm dev      # → http://localhost:3000
```

→ Details: [docs/03-webapp.md](docs/03-webapp.md)

LM Studio setup: load a tool-use capable model (e.g. `google/gemma-4-e4b`) with context ≥16384, REST API v1 in Anthropic-compatible mode — see the [LM Studio guide](https://github.com/jyje/pilot-deepagents-rubrics/blob/main/docs/05-lmstudio.md) from the sibling pilot. Switching to the official Anthropic API is a `.env`-only change.

## Documentation

→ [docs/README.md](docs/README.md) — architecture, contract spec, and how to write a new agent

## License

MIT © [jyje](https://github.com/jyje)
