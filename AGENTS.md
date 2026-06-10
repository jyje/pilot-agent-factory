# AGENTS.md — Project Context for AI Agents

> Updated: 2026-06-10

## 프로젝트 목적

LangGraph 하위 에이전트를 표준화된 플러그인 패키지로 개발하고 런타임에 불러오는 패턴의 파일럿.
계약(Phase 1) → 패키징(Phase 2) → 런타임 로딩(Phase 3)을 구현했으며, 수퍼바이저 조립(Phase 4)과
배포 파이프라인(Phase 5)은 범위 밖이다. 자매 파일럿: [pilot-deepagents-rubrics](https://github.com/jyje/pilot-deepagents-rubrics).

## 현재 상태 (2026-06-10)

Phase 1~3 완료. 테스트 28개 통과, LM Studio(`google/gemma-4-e4b`)로 4개 에이전트 실행 검증.

## 프로젝트 구조

```
pilot-agent-factory/
├── README.md / README-ko.md          ← 프로젝트 문서 (EN/KO)
├── AGENTS.md                         ← 이 파일: AI 에이전트용 컨텍스트
├── LICENSE                           ← MIT
├── docs/
│   ├── README.md                     ← 문서 인덱스
│   ├── 01-architecture(-ko).md       ← 4계층 패턴, 계약 명세, 로더 설계 결정
│   └── 02-writing-an-agent(-ko).md   ← 신규 에이전트 작성 가이드
└── src/                              ← uv workspace 루트
    ├── pyproject.toml                ← 호스트 앱 + workspace 정의
    ├── .env.sample / .env            ← LM Studio 기본값
    ├── main.py                       ← 호스트 CLI: list / run
    ├── doctor.py                     ← 진단: ENV/연결/탐색/추론
    ├── dropins/agent_pirate.py       ← 모드 B 드롭인 데모
    ├── tests/                        ← 계약/로더/에이전트 테스트 (LLM 불필요)
    └── packages/
        ├── agent-factory-sdk/        ← 계약, compat, 로더, llm 헬퍼, 테스트 하니스
        ├── agent-chitchat/           ← 예시 1: 단일 노드
        ├── agent-calculator/         ← 예시 2: ReAct 툴 루프
        └── agent-summarizer/         ← 예시 3: 2노드 + 커스텀 state 채널
```

## 실행 방법 요약

```bash
cd src/
cp .env.sample .env        # 기본값이 LM Studio (127.0.0.1:1234)
uv sync --dev

uv run pytest              # LLM 없이 전체 검증
uv run python doctor.py    # 엔드포인트 포함 진단
uv run python main.py list
uv run python main.py run calculator "What is (17 + 25) * 3?"
```

LM Studio: `lms server start` 후 `lms load google/gemma-4-e4b --context-length 16384 -y`.

## 핵심 설계 결정 (변경 시 docs/01-architecture.md도 갱신할 것)

- `build()`는 팩토리 — 임포트 시점 그래프 컴파일 금지, 모델은 `resolve_llm(config)`로만 획득
- `SubAgent`는 Protocol(상속 없음), manifest는 코드에 정의 (agent.yaml 없음 — 의도적)
- 에이전트의 `sdk_version`은 리터럴 문자열 (SDK_VERSION 임포트 금지)
- 로더는 실패 격리: 깨진 에이전트는 `LoadReport.errors`로 기록, 예외 전파 금지
- entry point 그룹명: `agent_factory.agents`, 드롭인 컨벤션: 모듈 레벨 `AGENT`

## 환경변수 (src/.env)

| 변수 | 필수 | 기본값 | 설명 |
|------|------|--------|------|
| `ANTHROPIC_API_KEY` | 필수 | — | LM Studio는 임의 값(`lm-studio`) 허용 |
| `ANTHROPIC_BASE_URL` | 선택 | (공식 API) | LM Studio: `http://127.0.0.1:1234` |
| `MAIN_MODEL` | 선택 | `claude-sonnet-4-6` | LM Studio: `google/gemma-4-e4b` |
