# 아키텍처

> [English](01-architecture.md)

## 4계층 패턴

```
1. 계약            agent-factory-sdk: AgentManifest + SubAgent 프로토콜
2. 패키징          에이전트 = entry point를 가진 pip 패키지
3. 로딩            AgentRegistry: entry points (모드 A) + 드롭인 파일 (모드 B)
4. 조립            수퍼바이저가 manifest로 하나의 멀티 에이전트 그래프를 구성
5. 오케스트레이션   최상위 deep agent: task 위임, 세션, 그래프 뷰
```

이 저장소는 Phase 1~5를 구현합니다 ([Phase 5 상세](04-phase5-plan-ko.md)). Phase 6(배포/import)은 같은 문서에 계획되어 있습니다.

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
- **state 계약 기본값은 messages-in/messages-out.** 더 풍부한 state를 갖는 에이전트(`agent-summarizer`의 `summary` 채널 참조)는 `output_schema`에 선언합니다. Phase 4 수퍼바이저가 이 스키마로 경계 간 state를 매핑해 하위 에이전트와 수퍼바이저 state를 느슨하게 결합합니다.

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

## 4계층 — 수퍼바이저 조립 (`agent_factory_sdk.supervisor`)

```
__start__ → supervisor ─┬→ <에이전트 어댑터> ─┐
                        ├→ <에이전트 어댑터> ─┤→ supervisor로 복귀
                        └→ FINISH → __end__  ┘
```

`build_supervisor(registry)`가 레지스트리에 로딩된 에이전트 전체를 하나의 그래프로 조립합니다. 동일한 manifest가 세 가지 용도로 쓰입니다:

| manifest 필드 | 용도 |
|---|---|
| `description` + `capabilities` | 라우터의 로스터 프롬프트 — 에이전트를 추가/제거하면 코드 수정 없이 라우팅 선택지가 바뀜 |
| `output_schema` | 어댑터가 `messages` 외 채널(예: `summarizer.summary`)을 수퍼바이저의 `artifacts[<agent>]`로 승격 |
| `name` + `version` | 모든 하위 에이전트 실행에 LangSmith/OTel 트레이스 태그(`agent:<name>@<version>`) 부여 |

설계 결정:

- **어댑터가 유일한 경계입니다.** 하위 에이전트는 `{"messages": ...}`만 받고, 새 메시지는 `add_messages` 리듀서로 합쳐지며 나머지는 `artifacts`로 갑니다. 양쪽 모두 상대의 state 구조를 모릅니다.
- **라우팅은 `route` 툴콜 한 번입니다** (LangChain이 권장하는 tool-calling 핸드오프 스타일). `_parse_decision`은 약한 로컬 모델을 위해 단계적으로 완화됩니다: 툴콜 → 텍스트 내 JSON → 텍스트 내 `FINISH` 리터럴 → 강제 FINISH. 알 수 없는 에이전트명은 FINISH로 강제되고 `route_trace`에 기록됩니다. 라우터는 자신의 라우팅 이력도 봅니다("You already consulted: …" — Anthropic이 비연속 system 메시지를 거부하므로 단일 시스템 메시지에 합쳐서 주입): 실기에서 관찰된 바, 작은 로컬 모델은 이 힌트가 없으면 방금 답한 에이전트로 재라우팅하는 경향이 있습니다.
- **종료는 프롬프트가 아닌 구조로 보장합니다.** `max_hops`(기본 6)가 LLM 호출 전에 라우터 노드에서 루프를 차단하므로, 혼란에 빠진 로컬 모델이 무한 루프를 돌 수 없습니다.
- **`route_trace`는 일급 state 채널입니다.** 모든 결정(완화 단계 포함)을 CLI(`main.py chat`), API(SSE `route` 이벤트), 웹앱에서 관찰할 수 있습니다.

## 5계층 — Deep 오케스트레이션 (`agent_factory_sdk.deep`, `viz`)

`build_deep_supervisor(registry, config, checkpointer)`가 수제 라우터를 deepagents 최상위로 대체합니다: 레지스트리 에이전트는 변경 없이 `CompiledSubAgent`로 연결되고(manifest의 `name`/`description` 사용), 파일시스템 툴 표면은 harness profile로 차단되며, 자동 general-purpose 하위 에이전트는 비활성화되어 하위 에이전트 위임이 유일한 작업 경로입니다. 두 수퍼바이저 모두 `checkpointer`를 받아 thread 단위 멀티턴 세션을 지원합니다. `viz.render_platform_mermaid`는 각 에이전트의 컴파일된 그래프 토폴로지에서 플랫폼 Mermaid 그림을 도출합니다. 상세 근거: [04-phase5-plan-ko.md](04-phase5-plan-ko.md).

## 테스트 하니스 (`agent_factory_sdk.testing`)

- `assert_agent_valid(agent)` — 한 번의 호출로 끝나는 CI 게이트: 프로토콜 형태, manifest 유효성, 호환성, 가짜 모델 주입 하에서 `build()`가 `Runnable`을 반환하는지.
- `ScriptedChatModel` — 고정된 응답 목록을 재생하고 `bind_tools()`를 no-op으로 구현해, calculator의 ReAct 루프까지 엔드포인트 없이 테스트에서 끝까지 돕니다.

## 알려진 한계 / 탈출구

모든 에이전트가 한 프로세스, 하나의 의존성 해석을 공유합니다. SDK가 `langgraph`/`langchain-core` 버전 밴드를 고정하며, 의존성이 공존 불가능한 에이전트는 별도 서비스로 분리해 원격(A2A) 호출로 전환해야 합니다 — 이 탈출구는 Phase 5 관심사로 여기서는 의도적으로 다루지 않습니다.
