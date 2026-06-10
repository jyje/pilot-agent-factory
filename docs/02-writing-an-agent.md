# Writing a New Agent

> [한국어](02-writing-an-agent-ko.md)

## Option 1 — A package (Mode A, recommended)

### 1. Scaffold

```
src/packages/agent-translator/
├── pyproject.toml
└── src/agent_translator/
    ├── __init__.py     # manifest + AGENT export
    └── graph.py        # build_graph(config) → compiled StateGraph
```

### 2. `pyproject.toml`

```toml
[project]
name = "agent-translator"
version = "0.1.0"
requires-python = ">=3.14,<3.15"
dependencies = ["agent-factory-sdk"]

[project.entry-points."agent_factory.agents"]
translator = "agent_translator:AGENT"          # ← discovery hook

[tool.uv.sources]
agent-factory-sdk = { workspace = true }

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/agent_translator"]
```

### 3. `__init__.py`

```python
from typing import Any
from agent_factory_sdk import AgentManifest
from langchain_core.runnables import Runnable

class TranslatorAgent:
    manifest = AgentManifest(
        name="translator",
        version="0.1.0",
        sdk_version="0.1.0",        # literal — the SDK version you built against
        description="Translates text between languages",
        capabilities=["translation"],
    )

    def build(self, config: dict[str, Any] | None = None) -> Runnable:
        from .graph import build_graph   # keep graph imports lazy
        return build_graph(config)

AGENT = TranslatorAgent()
```

### 4. `graph.py`

```python
from agent_factory_sdk import resolve_llm
from langgraph.graph import END, START, MessagesState, StateGraph

def build_graph(config=None):
    llm = resolve_llm(config)            # ← never construct your own client
    def node(state: MessagesState):
        return {"messages": [llm.invoke(state["messages"])]}
    builder = StateGraph(MessagesState)
    builder.add_node("translate", node)
    builder.add_edge(START, "translate")
    builder.add_edge("translate", END)
    return builder.compile()
```

### 5. Register, test, run

```bash
# add to src/pyproject.toml: dependencies + [tool.uv.sources] workspace entry
uv sync
uv run pytest                       # add a test using assert_agent_valid
uv run python main.py run translator "Translate 'hello' to Korean"
```

Minimal test:

```python
from agent_factory_sdk.testing import ScriptedChatModel, assert_agent_valid
from agent_translator import AGENT

def test_contract():
    assert_agent_valid(AGENT)

def test_replies():
    graph = AGENT.build({"llm": ScriptedChatModel(responses=["안녕하세요"])})
    assert graph.invoke({"messages": [("user", "hello")]})["messages"][-1].content == "안녕하세요"
```

## Option 2 — A drop-in file (Mode B)

Put a single `.py` file in `src/dropins/` with a module-level `AGENT` satisfying the same contract (see [dropins/agent_pirate.py](../src/dropins/agent_pirate.py)). No install step — `main.py list` picks it up on the next run. Files starting with `_` are skipped.

Drop-ins may import the SDK and anything in the host venv, but cannot bring their own dependencies — that's what packages are for.

## Rules of thumb

- Never compile a graph at import time; do it in `build()`.
- Always get the model via `resolve_llm(config)` so tests and hosts can inject.
- `sdk_version` is a literal string, not an import of `SDK_VERSION` — importing the installed version would make the compat gate vacuous.
- Declare non-default state channels in `input_schema`/`output_schema`.
- Give `capabilities` real routing value: they become the supervisor's routing prompt in Phase 4.
