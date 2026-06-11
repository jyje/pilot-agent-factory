# AGENTS.md — Project Context for AI Agents

> Updated: 2026-06-12

## 프로젝트 목적

LangGraph 하위 에이전트를 표준화된 플러그인 패키지로 개발하고 런타임에 불러오는 패턴의 파일럿.
계약(Phase 1) → 패키징(Phase 2) → 런타임 로딩(Phase 3) → 수퍼바이저 조립(Phase 4) →
deep agent 오케스트레이션(Phase 5: 최상위 deepagents, 그래프 뷰, 멀티턴 세션)을 구현했고,
배포/import 파이프라인(Phase 6)은 [docs/04-phase5-plan-ko.md](docs/04-phase5-plan-ko.md)에 계획되어 있다.
자매 파일럿: [pilot-deepagents-rubrics](https://github.com/jyje/pilot-deepagents-rubrics).

## 현재 상태 (2026-06-12)

Phase 1~5 완료. 테스트 41개 통과. LM Studio(`google/gemma-4-e4b`)로 실기 검증:
deep supervisor의 task 위임, 멀티턴 세션 메모리("Jay" 회상), 플랫폼 구조 다이얼로그
(스크린샷: docs/assets/scenario-4~6).

## 프로젝트 구조

```
pilot-agent-factory/
├── README.md / README-ko.md          ← 프로젝트 문서 (EN/KO)
├── AGENTS.md                         ← 이 파일: AI 에이전트용 컨텍스트
├── ONESHOT.md / GOAL.md              ← 최초 원샷 구축 기록 / 원본 프롬프트
├── docs/
│   ├── 01-architecture(-ko).md       ← 4계층 패턴, 계약/로더/수퍼바이저 설계 결정
│   ├── 02-writing-an-agent(-ko).md   ← 신규 에이전트 작성 가이드
│   ├── 03-webapp(-ko).md             ← app/ 소비자 (FastAPI + Next.js) 가이드
│   ├── 04-phase5-plan(-ko).md        ← Phase 5 계획: zip/tar/git import
│   └── assets/                       ← 스크린샷
├── src/                              ← 플랫폼: uv workspace
│   ├── main.py                       ← 호스트 CLI: list / run / chat(REPL) / graph
│   ├── doctor.py                     ← 진단: ENV/연결/탐색/추론
│   ├── dropins/agent_pirate.py       ← 모드 B 드롭인 데모
│   ├── tests/                        ← 계약/로더/에이전트/수퍼바이저/deep (LLM 불필요)
│   └── packages/
│       ├── agent-factory-sdk/        ← contract, compat, loader, supervisor, deep, viz, llm, testing
│       ├── agent-chitchat/           ← 예시 1: 단일 노드
│       ├── agent-calculator/         ← 예시 2: ReAct 툴 루프
│       └── agent-summarizer/         ← 예시 3: 2노드 + 커스텀 state 채널
└── app/                              ← 소비자: path 의존성으로 src 패키지 참조
    ├── backend/                      ← FastAPI: /api/agents, /api/chat (SSE)
    └── frontend/                     ← Next.js 16 + AI Elements + shadcn/ui
```

## 실행 방법 요약

```bash
# 플랫폼 (src/)
cd src/
cp .env.sample .env        # 기본값이 LM Studio (127.0.0.1:1234)
uv sync --dev
uv run pytest              # LLM 없이 전체 검증 (41 tests)
uv run python doctor.py
uv run python main.py chat "What is (17 + 25) * 3?"   # deep supervisor 위임 (--simple: Phase 4 라우터)
uv run python main.py chat                            # 멀티턴 REPL (세션 메모리)
uv run python main.py graph                           # Mermaid 플랫폼 구조

# 웹앱 (app/)
cd app/backend && uv sync && uv run fastapi dev src/agent_factory_backend/server.py
cd app/frontend && pnpm install && pnpm dev            # http://localhost:3000
```

LM Studio: `lms server start` 후 `lms load google/gemma-4-e4b --context-length 16384 -y`.

## 핵심 설계 결정 (변경 시 docs/01-architecture.md도 갱신할 것)

- `build()`는 팩토리 — 임포트 시점 그래프 컴파일 금지, 모델은 `resolve_llm(config)`로만 획득
- `SubAgent`는 Protocol(상속 없음), manifest는 코드에 정의 (agent.yaml 없음 — 의도적)
- 에이전트의 `sdk_version`은 리터럴 문자열 (SDK_VERSION 임포트 금지)
- 로더는 실패 격리: 깨진 에이전트는 `LoadReport.errors`로 기록, 예외 전파 금지
- entry point 그룹명: `agent_factory.agents`, 드롭인 컨벤션: 모듈 레벨 `AGENT`
- 수퍼바이저(Phase 4): `route` 툴콜 1회로 라우팅, `_parse_decision`은 단계적 완화(툴콜→JSON→FINISH 리터럴→강제 FINISH),
  `max_hops`(기본 6)로 구조적 종료, 어댑터가 messages만 전달하고 extras는 `artifacts[<agent>]`로 승격
- deep supervisor(Phase 5, 기본): deepagents `CompiledSubAgent`로 하위 연결, `anthropic` 프로바이더에
  HarnessProfile 등록으로 파일시스템 툴 전체 차단(미들웨어 제거는 0.6.8부터 금지) + general-purpose 비활성화.
  세션은 checkpointer × thread_id (백엔드/CLI REPL 모두 MemorySaver — 인프로세스)
- 프론트엔드: AI Elements + shadcn만 사용, 도메인 래핑은 `app/frontend/src/components/custom/`에만.
  AI Elements는 vendored — Base UI/Radix 차이 패치가 주석으로 표시되어 있음 (docs/03-webapp.md 참조)

## 환경변수 (src/.env — app/backend가 폴백으로 공유)

| 변수 | 필수 | 기본값 | 설명 |
|------|------|--------|------|
| `ANTHROPIC_API_KEY` | 필수 | — | LM Studio는 임의 값(`lm-studio`) 허용 |
| `ANTHROPIC_BASE_URL` | 선택 | (공식 API) | LM Studio: `http://127.0.0.1:1234` |
| `MAIN_MODEL` | 선택 | `claude-sonnet-4-6` | LM Studio: `google/gemma-4-e4b` |
| `AGENT_DROPINS` | 선택 | `src/dropins` | 백엔드 드롭인 디렉토리 |
| `NEXT_PUBLIC_API_BASE` | 선택 | `http://127.0.0.1:8000` | 프론트 → 백엔드 주소 |
