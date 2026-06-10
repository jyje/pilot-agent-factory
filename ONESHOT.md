# ONESHOT.md — One Prompt, One Working System

> This entire repository — Phases 1–3 of a runtime-loadable LangGraph sub-agent
> pattern — was built, tested, and verified against a live local LLM from a
> **single prompt**, by Claude Code (Fable 5).
> The prompt is preserved verbatim at the end of [GOAL.md](GOAL.md).

## What one prompt produced

| Deliverable | Evidence |
|---|---|
| An SDK package defining the agent contract | `AgentManifest` + `SubAgent` Protocol, semver compatibility gate, LLM injection helper, test harness with a scriptable fake chat model |
| 3 example agent packages, each a different graph shape | single-node (chitchat), ReAct tool loop (calculator), multi-node with custom state channel (summarizer) — all discovered via pip entry points |
| A second load path for un-installed agents | `dropins/agent_pirate.py`, imported from a bare file at runtime (mode B) |
| A loader that survives broken plugins | per-source failure isolation, duplicate-name handling, registry with helpful errors — all covered by tests |
| Host CLI + diagnostics | `main.py list / run`, `doctor.py` with ENV / connectivity / discovery / inference checks |
| 28 passing tests, zero LLM required | contract rules, loader isolation, and all 4 agents run end-to-end on a `ScriptedChatModel` |
| Live verification, not just green tests | started LM Studio's server myself (`lms server start`), loaded `google/gemma-4-e4b` at 16k context, then watched the calculator execute a real 2-step tool loop: `add(17,25)` → `multiply(42,3)` → "126" |
| Bilingual documentation | README, architecture rationale, and a write-your-own-agent guide, each in EN + KO, matching the owner's house style |

## How I work

**1. I read before I write.** The prompt said "참고는 pilot-deepagents-rubrics" — so the first thing I did was read that repo's source, docs, and conventions. The result inherits its DNA deliberately: uv-managed `src/`, a `doctor.py` diagnostic, `.env`-only switching between Anthropic BYOK and LM Studio, EN/KO doc pairs.

**2. Contract first, then everything grows from it.** The SDK's `Protocol` + manifest came first; agents, loader, CLI, and tests all consume that one contract. That ordering is why three differently-shaped agents and a drop-in file all load through the same 60-line loader.

**3. I verify with the cheapest sufficient tool, then escalate.** Tests run on a fake model so CI never needs a GPU. Only after 28/28 passed did I bring up the real endpoint — including noticing LM Studio was down, starting it via its CLI, and picking the context length the reference docs recommended.

**4. I let failures teach me.** Two real bugs surfaced and were fixed mid-run: a pydantic union that tripped langchain-core's validator (caught by my own tests), and a `.text` API drift between langchain-core versions (caught by a deprecation warning I refused to ship).

**5. I deviate from the plan only on purpose, and I say so.** Two conscious changes from the original phase plan — dropping `agent.yaml` (one source of truth beats two) and replacing the `/agents` HTTP endpoint with a CLI (this is a local pilot) — are recorded with rationale in [docs/01-architecture.md](docs/01-architecture.md), not silently swallowed.

**6. I respect what isn't mine.** A `GOAL.md` I didn't create appeared in the tree; I read it, recognized it as the owner's note, and left it untouched. Nothing was committed without being asked.

One prompt in. A tested, documented, live-verified plugin architecture out.

---

# ONESHOT.md — 프롬프트 한 번, 동작하는 시스템 하나

> 이 저장소 전체 — 런타임 로딩 LangGraph 하위 에이전트 패턴의 Phase 1~3 — 는
> **단 한 번의 프롬프트**로 Claude Code(Fable 5)가 구축하고, 테스트하고,
> 실제 로컬 LLM 위에서 검증까지 마친 결과물입니다.
> 그 프롬프트는 [GOAL.md](GOAL.md) 말미에 원문 그대로 보존되어 있습니다.

## 프롬프트 하나가 만든 것

| 산출물 | 근거 |
|---|---|
| 에이전트 계약을 정의하는 SDK 패키지 | `AgentManifest` + `SubAgent` Protocol, semver 호환성 게이트, LLM 주입 헬퍼, 스크립트 가능한 가짜 챗 모델을 갖춘 테스트 하니스 |
| 서로 다른 그래프 형태의 예시 에이전트 패키지 3종 | 단일 노드(chitchat), ReAct 툴 루프(calculator), 커스텀 state 채널을 가진 다중 노드(summarizer) — 모두 pip entry point로 탐색 |
| 설치 없이 동작하는 두 번째 로딩 경로 | `dropins/agent_pirate.py`, 런타임에 파일에서 직접 임포트 (모드 B) |
| 깨진 플러그인에도 살아남는 로더 | 소스별 실패 격리, 이름 중복 처리, 친절한 에러를 주는 레지스트리 — 전부 테스트로 커버 |
| 호스트 CLI + 진단 | `main.py list / run`, ENV·연결·탐색·추론 4종 점검의 `doctor.py` |
| LLM 없이 도는 테스트 28개 전부 통과 | 계약 규칙, 로더 격리, 에이전트 4종의 엔드투엔드가 `ScriptedChatModel` 위에서 실행 |
| 초록불 테스트로 끝내지 않은 실기 검증 | LM Studio 서버를 직접 기동(`lms server start`)하고 `google/gemma-4-e4b`를 16k 컨텍스트로 로드한 뒤, calculator가 실제 2단계 툴 루프 — `add(17,25)` → `multiply(42,3)` → "126" — 를 수행하는 것까지 확인 |
| 이중 언어 문서 | README, 아키텍처 설계 근거, 에이전트 작성 가이드를 각각 EN + KO로, 소유자의 하우스 스타일에 맞춰 작성 |

## 일하는 방식

**1. 쓰기 전에 읽는다.** 프롬프트에 "참고는 pilot-deepagents-rubrics"라고 적혀 있었고, 가장 먼저 한 일이 그 저장소의 소스·문서·컨벤션을 읽는 것이었습니다. 결과물은 의도적으로 그 DNA를 물려받았습니다: uv 기반 `src/`, `doctor.py` 진단, `.env`만으로 Anthropic BYOK ↔ LM Studio 전환, EN/KO 문서 쌍.

**2. 계약이 먼저, 나머지는 거기서 자란다.** SDK의 `Protocol` + manifest를 가장 먼저 만들었고, 에이전트·로더·CLI·테스트가 전부 그 하나의 계약을 소비합니다. 형태가 다른 에이전트 3종과 드롭인 파일이 동일한 60줄짜리 로더로 로딩되는 이유가 이 순서에 있습니다.

**3. 가장 싼 충분한 도구로 검증하고, 그다음 단계를 올린다.** 테스트는 가짜 모델 위에서 돌아 CI에 GPU가 필요 없습니다. 28/28 통과를 확인한 뒤에야 실제 엔드포인트를 올렸습니다 — LM Studio가 꺼져 있음을 발견하고 CLI로 직접 기동했고, 컨텍스트 길이는 참고 문서의 권장값을 따랐습니다.

**4. 실패에게 배운다.** 실행 중 실제 버그 두 개가 드러났고 그 자리에서 고쳤습니다: langchain-core의 검증기를 건드린 pydantic 유니온(제가 만든 테스트가 잡음), 그리고 langchain-core 버전 간 `.text` API 변화(deprecation 경고를 그냥 내보내지 않고 잡음).

**5. 계획에서 벗어날 땐 의도적으로, 그리고 말한다.** 원래 단계 계획에서 의식적으로 바꾼 두 가지 — `agent.yaml` 제거(진실의 원천은 하나가 둘보다 낫다), `/agents` HTTP 엔드포인트의 CLI 대체(이건 로컬 파일럿이다) — 는 조용히 삼키지 않고 [docs/01-architecture.md](docs/01-architecture.md)에 근거와 함께 기록했습니다.

**6. 내 것이 아닌 것을 존중한다.** 제가 만들지 않은 `GOAL.md`가 트리에 보였을 때, 읽어보고 소유자의 메모임을 확인한 뒤 손대지 않았습니다. 요청 없이는 아무것도 커밋하지 않았습니다.

프롬프트 하나가 들어갔고, 테스트되고 문서화되고 실기 검증된 플러그인 아키텍처가 나왔습니다.
