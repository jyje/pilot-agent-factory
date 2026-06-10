Python LangGraph의 에이전트 개발에 있어서 하위 에이전트를 표준화된 패키지 형태로 개발하고 런타임에 파일을 불러오는 패턴을 고안해주세요. 구현계획이 필요합니다

---

LangGraph 하위 에이전트를 "플러그인 패키지"로 표준화하는 패턴을 제안합니다. 핵심은 **계약(Contract) → 패키징 → 동적 로딩 → 수퍼바이저 조립**의 4계층입니다.

## 패턴 설계

**1. 계약 정의 (agent contract)**

모든 하위 에이전트가 따르는 인터페이스를 별도 SDK 패키지(`myorg-agent-sdk`)로 분리합니다.

```python
# myorg_agent_sdk/contract.py
from typing import Protocol
from pydantic import BaseModel
from langchain_core.runnables import Runnable

class AgentManifest(BaseModel):
    name: str
    version: str
    sdk_version: str          # 호환성 체크용
    description: str
    input_schema: dict        # JSON Schema
    output_schema: dict
    capabilities: list[str]   # 수퍼바이저 라우팅 힌트

class SubAgent(Protocol):
    manifest: AgentManifest
    def build(self, config: dict) -> Runnable:
        """컴파일된 StateGraph 또는 Runnable 반환"""
        ...
```

핵심은 `build()`가 **컴파일된 그래프를 반환하는 팩토리**라는 점입니다. 모듈 임포트 시점에 그래프를 만들지 않아야 LLM 클라이언트 주입, config 오버라이드가 가능해집니다.

**2. 하위 에이전트 패키지 구조**

```
agent-researcher/
├── pyproject.toml          # entry point 선언
├── agent.yaml              # manifest (메타데이터)
└── src/agent_researcher/
    ├── __init__.py         # SubAgent 구현체 export
    ├── graph.py            # StateGraph 정의
    └── state.py            # pydantic state 모델
```

```toml
# pyproject.toml
[project.entry-points."myorg.agents"]
researcher = "agent_researcher:ResearcherAgent"
```

**3. 런타임 로더 — 2가지 모드**

```python
# loader.py
from importlib.metadata import entry_points
import importlib.util, sys

def load_installed_agents() -> dict[str, SubAgent]:
    """모드 A: pip 설치된 패키지에서 entry point 탐색"""
    agents = {}
    for ep in entry_points(group="myorg.agents"):
        cls = ep.load()
        agent = cls()
        check_compat(agent.manifest)   # sdk_version semver 검증
        agents[agent.manifest.name] = agent
    return agents

def load_from_path(path: str, module_name: str) -> SubAgent:
    """모드 B: 파일 경로에서 직접 로딩 (PVC/ConfigMap 마운트용)"""
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod.AGENT   # 모듈 레벨 컨벤션
```

모드 A(entry points)가 기본이고, 모드 B는 K8s에서 이미지 재빌드 없이 PVC/initContainer로 wheel을 떨어뜨려 핫스왑할 때 씁니다. 모드 B를 쓸 경우 `pip install --target /mnt/agents` 후 `sys.path` 추가 방식이 의존성 관리 면에서 raw 파일 로딩보다 안전합니다.

**4. 수퍼바이저 조립**

```python
# supervisor.py
agents = load_installed_agents()
builder = StateGraph(SupervisorState)

for name, agent in agents.items():
    sub = agent.build(config={"llm": llm})
    # state 매핑 어댑터로 감싸서 노드 등록
    builder.add_node(name, make_adapter(sub, agent.manifest))

builder.add_node("supervisor", make_router(agents))  # capabilities 기반 라우팅
```

manifest의 `input/output_schema`로 수퍼바이저 state ↔ 에이전트 state 간 매핑 어댑터를 자동 생성하면, 에이전트가 수퍼바이저의 state 구조를 몰라도 됩니다(느슨한 결합).

## 구현 계획

**Phase 1 — 계약 (1주)**: SDK 패키지에 `SubAgent` Protocol, `AgentManifest`, semver 호환성 검사, 테스트 하니스(`assert_agent_valid()`) 작성. 여기서 결정할 핵심 이슈는 state 전달 방식 — 전체 state 공유 vs message-only handoff vs schema 매핑. **schema 매핑을 권장**합니다.

**Phase 2 — 레퍼런스 에이전트 + cookiecutter (1주)**: 템플릿 저장소를 만들어 신규 에이전트 스캐폴딩을 표준화. CI에서 manifest 검증 + 단위 테스트 강제.

**Phase 3 — 로더/레지스트리 (1주)**: 모드 A 구현 → 모드 B 추가. 로딩 실패 시 격리(한 에이전트 오류가 전체 부팅을 막지 않게), 로딩된 에이전트 목록 `/agents` 엔드포인트로 노출.

**Phase 4 — 수퍼바이저 통합 (1~2주)**: 어댑터 자동 생성, capabilities 기반 동적 라우팅 프롬프트 생성, LangSmith/OTel 트레이싱에 agent name·version 태깅.

**Phase 5 — 배포 파이프라인**: 사내 PyPI(또는 GitLab/Artifactory)에 wheel 게시 → 수퍼바이저 이미지 빌드 시 `requirements-agents.txt`로 버전 고정. 핫스왑이 필요하면 initContainer가 wheel을 PVC에 설치하고 메인 컨테이너가 `sys.path`에 추가 + 재시작(rollout) 트리거. 진짜 무중단 리로드는 모듈 캐시 문제로 복잡도가 높아서, K8s에서는 rollout restart가 더 단순하고 안전합니다.

리스크 한 가지: 에이전트별 의존성 충돌입니다. 같은 프로세스에 로딩하는 한 피할 수 없으므로, SDK에서 허용 의존성 범위(langgraph, langchain-core 버전 밴드)를 강제하고, 충돌이 큰 에이전트는 별도 서비스로 분리해 A2A/원격 호출로 전환하는 escape hatch를 설계에 남겨두세요.

원하시면 Phase 1의 SDK 패키지 코드를 실제 동작하는 형태로 만들어 드릴 수 있습니다.

---
지난 대화 입니다
phase 3까지 구현해주세요. 로컬 실행할거에요. 엔드포인트는 lm studio 입니다 예시 에이전트 3개가 들어갑니다. 참고는 ~/repo/jyje/pilot-deepagents-rubrics 입니다. 문서와 구현 모두 적극 참조 해주세요
