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
Contract (SDK)  →  Packaging (entry points)  →  Runtime loading  →  Supervisor assembly
   Phase 1            Phase 2                      Phase 3            Phase 4 (future)
```

Every sub-agent is a pip package that exposes a `manifest` (metadata + routing hints) and a `build()` factory returning a compiled `StateGraph`. The host discovers agents through two modes:

- **Mode A — entry points**: pip-installed packages registered under the `agent_factory.agents` group (default)
- **Mode B — drop-ins**: plain `.py` files imported from a directory at runtime (the local stand-in for a mounted PVC/ConfigMap)

One broken agent never blocks the host: load failures are isolated and reported per source.

```
                    host (main.py)
                         │ discover
            ┌────────────┼─────────────┐
            ▼            ▼             ▼
     entry points   entry points    dropins/*.py
    agent-chitchat  agent-calculator  agent_pirate.py
    agent-summarizer        │
            └────────────┬──┘
                         ▼
              SubAgent.build(config) → compiled StateGraph
```

## What's inside

| Package | Role |
|---------|------|
| `agent-factory-sdk` | Contract (`AgentManifest`, `SubAgent`), semver compat gate, loader/registry, test harness |
| `agent-chitchat` | Example 1 — single-node conversational graph |
| `agent-calculator` | Example 2 — ReAct tool loop (add/subtract/multiply/divide) |
| `agent-summarizer` | Example 3 — two-node pipeline with a custom `summary` state channel |
| `dropins/agent_pirate.py` | Mode B demo — loaded from a file, never pip-installed |

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

# run one
uv run python main.py run calculator "What is (17 + 25) * 3?"
uv run python main.py run summarizer "<long text>"

# LLM-free test suite (contract + loader + all agents)
uv run pytest
```

LM Studio setup: load a tool-use capable model (e.g. `google/gemma-4-e4b`) with context ≥16384, REST API v1 in Anthropic-compatible mode — see the [LM Studio guide](https://github.com/jyje/pilot-deepagents-rubrics/blob/main/docs/05-lmstudio.md) from the sibling pilot. Switching to the official Anthropic API is a `.env`-only change.

## Documentation

→ [docs/README.md](docs/README.md) — architecture, contract spec, and how to write a new agent

## License

MIT © [jyje](https://github.com/jyje)
