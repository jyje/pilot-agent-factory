# 아키텍처

> [English](01-architecture.md)

## 4계층 패턴

```
1. 계약        agent-factory-sdk: AgentManifest + SubAgent 프로토콜
2. 패키징      에이전트 = entry point를 가진 pip 패키지
3. 로딩        AgentRegistry: entry points (모드 A) + 드롭인 파일 (모드 B)
4. 조립        수퍼바이저가 manifest로 노드를 구성   ← Phase 4, 본 저장소 범위 밖
```

이 저장소는 Phase 1~3을 구현합니다.

## 1계층 — 계약 (`agent_factory_sdk.contract`)

```python
class AgentManifest(BaseModel):
    name: str             # 고유 id (kebab/snake case)
    version: str          # 에이전트 semver
    sdk_version: str      # 빌드 당시 기준 SDK 버전
    description: str
    capabilities: list[str]      # 향후 수퍼바이저 라우팅 힌트
    input_schema: dict           # JSON Schema, 기본값 messages-in
    output_schema: dict          # JSON Schema, 기본값 messages-out

@runtime_checkable
class SubAgent(Protocol):
    manifest: AgentManifest
    def build(self, config: dict | None = None) -> Runnable: ...
```

핵심 결정:

- **`build()`는 팩토리입니다.** 임포트 시점에 그래프를 컴파일하지 않습니다. 덕분에 호스트가 LLM을 주입(`config["llm"]`)할 수 있고, 테스트 하니스는 네트워크 없이 `ScriptedChatModel`로 모든 에이전트를 실행합니다. 에이전트는 `resolve_llm(config)`로 모델을 얻습니다 — 주입된 클라이언트 우선, 없으면 환경변수 기반 `ChatAnthropic`.
- **`SubAgent`는 base class가 아닌 `Protocol`입니다.** 에이전트 패키지는 SDK의 `AgentManifest`와 헬퍼에만 의존하고 SDK 내부를 상속하지 않아 호환성 표면이 작습니다.
- **manifest는 별도 `agent.yaml`이 아닌 코드에 둡니다.** yaml manifest도 검토했지만(플러그인 시스템에서 흔한 방식) 진실의 원천이 둘이 되면 코드와 어긋납니다. 임포트 시점 pydantic 검증으로 같은 보장을 하나의 산출물로 얻습니다. 비-Python 레지스트리가 필요해지면 `manifest.model_dump_json()`으로 내보내면 됩니다.
- **state 계약 기본값은 messages-in/messages-out.** 더 풍부한 state를 갖는 에이전트(`agent-summarizer`의 `summary` 채널 참조)는 `output_schema`에 선언합니다. Phase 4 수퍼바이저가 이 스키마로 state 매핑 어댑터를 생성해 하위 에이전트와 수퍼바이저 state를 느슨하게 결합합니다.

## 호환성 게이트 (`compat.py`)

모든 로딩은 `check_compat(manifest)`를 거칩니다:

- major 버전이 일치해야 하고,
- SDK가 `0.x`인 동안에는 minor도 일치해야 합니다 (semver에서 `0.x` minor는 breaking).

비호환 에이전트는 크래시가 아니라 로딩 에러로 기록됩니다.

## 3계층 — 로더 (`agent_factory_sdk.loader`)

```
AgentRegistry.discover(dropin_dir=...)
 ├── 모드 A: importlib.metadata.entry_points(group="agent_factory.agents")
 └── 모드 B: dropins/*.py를 spec-from-file로 임포트, 모듈 레벨 AGENT
```

| | 모드 A (entry points) | 모드 B (드롭인) |
|--|----------------------|----------------|
| 단위 | pip 패키지 | 단일 `.py` 파일 |
| 의존성 관리 | pip/uv가 해석 | 호스트 venv에 의존 |
| 용도 | 기본, CI 검증된 릴리스 | 마운트 볼륨 핫스왑, 실험 |
| 탐색 | `[project.entry-points."agent_factory.agents"]` | 디렉토리 스캔, `AGENT` 속성 |

**실패 격리**가 로더의 핵심 불변식입니다: entry point/파일별로 `try`로 감싸 실패를 `LoadReport`의 `LoadError(source, error)`로 기록하고 예외를 전파하지 않습니다. 이름 충돌 시 먼저 로딩된 쪽(설치 패키지가 드롭인보다 우선)을 유지하고 중복을 에러로 기록합니다. 호스트는 로딩에 성공한 에이전트만으로 기동하며, `main.py list`가 두 섹션을 모두 출력합니다.

Kubernetes에서 모드 B의 권장 형태는 raw 파일이 아니라 *PVC에 wheel 설치*(`pip install --target`) + `sys.path` 확장입니다 — raw 드롭인은 로컬 개발/데모용입니다. 프로세스 내 진짜 핫 리로드는 의도적으로 범위에서 제외했습니다(모듈 캐시 무효화의 복잡도 대비 `rollout restart`가 단순하고 안전).

## 테스트 하니스 (`agent_factory_sdk.testing`)

- `assert_agent_valid(agent)` — 한 번의 호출로 끝나는 CI 게이트: 프로토콜 형태, manifest 유효성, 호환성, 가짜 모델 주입 하에서 `build()`가 `Runnable`을 반환하는지.
- `ScriptedChatModel` — 고정된 응답 목록을 재생하고 `bind_tools()`를 no-op으로 구현해, calculator의 ReAct 루프까지 엔드포인트 없이 테스트에서 끝까지 돕니다.

## 알려진 한계 / 탈출구

모든 에이전트가 한 프로세스, 하나의 의존성 해석을 공유합니다. SDK가 `langgraph`/`langchain-core` 버전 밴드를 고정하며, 의존성이 공존 불가능한 에이전트는 별도 서비스로 분리해 원격(A2A) 호출로 전환해야 합니다 — 이 탈출구는 Phase 5 관심사로 여기서는 의도적으로 다루지 않습니다.
