# 신규 에이전트 작성 가이드

> [English](02-writing-an-agent.md)

## 방법 1 — 패키지 (모드 A, 권장)

### 1. 스캐폴드

```
src/packages/agent-translator/
├── pyproject.toml
└── src/agent_translator/
    ├── __init__.py     # manifest + AGENT export
    └── graph.py        # build_graph(config) → 컴파일된 StateGraph
```

### 2. `pyproject.toml`

```toml
[project]
name = "agent-translator"
version = "0.1.0"
requires-python = ">=3.14,<3.15"
dependencies = ["agent-factory-sdk"]

[project.entry-points."agent_factory.agents"]
translator = "agent_translator:AGENT"          # ← 탐색 훅

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
        sdk_version="0.1.0",        # 리터럴 — 빌드 당시 기준 SDK 버전
        description="Translates text between languages",
        capabilities=["translation"],
    )

    def build(self, config: dict[str, Any] | None = None) -> Runnable:
        from .graph import build_graph   # 그래프 임포트는 lazy하게
        return build_graph(config)

AGENT = TranslatorAgent()
```

### 4. `graph.py`

```python
from agent_factory_sdk import resolve_llm
from langgraph.graph import END, START, MessagesState, StateGraph

def build_graph(config=None):
    llm = resolve_llm(config)            # ← 클라이언트를 직접 만들지 말 것
    def node(state: MessagesState):
        return {"messages": [llm.invoke(state["messages"])]}
    builder = StateGraph(MessagesState)
    builder.add_node("translate", node)
    builder.add_edge(START, "translate")
    builder.add_edge("translate", END)
    return builder.compile()
```

### 5. 등록, 테스트, 실행

```bash
# src/pyproject.toml에 추가: dependencies + [tool.uv.sources] workspace 항목
uv sync
uv run pytest                       # assert_agent_valid 기반 테스트 추가
uv run python main.py run translator "Translate 'hello' to Korean"
```

최소 테스트:

```python
from agent_factory_sdk.testing import ScriptedChatModel, assert_agent_valid
from agent_translator import AGENT

def test_contract():
    assert_agent_valid(AGENT)

def test_replies():
    graph = AGENT.build({"llm": ScriptedChatModel(responses=["안녕하세요"])})
    assert graph.invoke({"messages": [("user", "hello")]})["messages"][-1].content == "안녕하세요"
```

## 방법 2 — 드롭인 파일 (모드 B)

같은 계약을 만족하는 모듈 레벨 `AGENT`를 가진 `.py` 파일 하나를 `src/dropins/`에 넣으면 됩니다([dropins/agent_pirate.py](../src/dropins/agent_pirate.py) 참조). 설치 과정 없이 다음 `main.py list` 실행에서 바로 잡힙니다. `_`로 시작하는 파일은 건너뜁니다.

드롭인은 SDK와 호스트 venv에 있는 것은 임포트할 수 있지만, 자체 의존성은 가져올 수 없습니다 — 그게 필요하면 패키지로 만드세요.

## 원칙

- 임포트 시점에 그래프를 컴파일하지 말 것 — `build()`에서 할 것.
- 모델은 항상 `resolve_llm(config)`로 얻을 것 — 테스트/호스트가 주입할 수 있도록.
- `sdk_version`은 `SDK_VERSION` 임포트가 아닌 리터럴 문자열 — 설치된 버전을 임포트하면 호환성 게이트가 무의미해집니다.
- 기본값 외 state 채널은 `input_schema`/`output_schema`에 선언할 것.
- `capabilities`에 실질적 라우팅 가치를 담을 것 — 수퍼바이저 라우팅 프롬프트(`agent_factory_sdk.supervisor`)에 그대로 주입되어 에이전트가 선택되는 시점을 직접 결정합니다.
