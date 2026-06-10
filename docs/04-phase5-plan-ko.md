# Phase 5 계획 — 배포 & Import

> [English](04-phase5-plan.md) · 상태: **계획됨** (미구현)

## 목표

*다른 어딘가*에 있는 에이전트를 호스트 재빌드 없이 실행 중인 시스템에 들여오는 것. import 소스는 둘, 컨벤션은 하나:

```
agent-factory import ./agent-translator-0.1.0.zip          # zip / tar.gz 아카이브
agent-factory import git+https://github.com/me/agent-x.git  # git 저장소 (아래 컨벤션)
agent-factory import git+https://...@v0.2.0                 # ref 고정
```

2026년 생태계 방향과 일치합니다: 에이전트 스킬의 npm 스타일 한 줄 설치(skills.sh, MCP 허브들)와 기계 판독 capability 카드(A2A의 `agent.json`). 우리 `AgentManifest`가 이미 카드 역할을 하고 있으므로, Phase 5는 그 주변에 설치 파이프라인을 더하는 것입니다.

## Import 컨벤션

아카이브에서 풀리든 git에서 클론되든, import 가능한 단위는 예시 에이전트들과 정확히 같은 모양의 디렉토리여야 합니다:

```
agent-x/
├── pyproject.toml      # 필수: [project.entry-points."agent_factory.agents"]
│                       #       agent-factory-sdk 의존성 (버전 밴드 내)
├── src/agent_x/
│   ├── __init__.py     # AGENT (sdk_version 포함 manifest, build())
│   └── graph.py
└── tests/              # 권장: 최소한 assert_agent_valid()
```

검증 게이트 (설치 전):
1. `pyproject.toml`이 파싱되고 `agent_factory.agents` entry point를 정확히 하나 선언.
2. 선언된 의존성이 SDK 허용 밴드(`langgraph`, `langchain-core`, `agent-factory-sdk`) 안에 있을 것 — 그 외는 명시적 `--allow-deps` 플래그 필요.
3. 설치 후: 기존 레지스트리로 로딩(`check_compat` + `ScriptedChatModel` 기반 `assert_agent_valid`)하되, 악의적 `import`가 호스트를 죽일 수 없도록 서브프로세스에서 수행.

## 파이프라인 설계

```
아카이브/git → 스테이징 디렉토리 → 검증 → uv pip install --target <agents-site>/<name>@<version>
            → 레지스트리 갱신 (entry points 재탐색) → 보고 (loaded | rejected + 사유)
```

- **`agent_factory_sdk.importer`** (신규 모듈): `import_archive(path)`, `import_git(url, ref)` — 둘 다 로더가 이미 쓰는 `LoadReport` 형태를 반환. 실패는 격리되고 예외를 전파하지 않음.
- **버전별 설치 디렉토리** (`<name>@<version>`)로 롤백은 디렉토리 삭제 한 번; `sys.path`에는 활성 버전만.
- **Git 모드**는 `git clone --depth 1` (+ 선택적 `--ref`); 락파일(`agents.lock`)에 커밋 해시를 기록해 재현 가능한 설치 보장.
- **K8s 형태**는 Phase 3 권장안 유지: initContainer가 PVC에 `agent-factory import` 실행 후 메인 컨테이너 재시작. 프로세스 내 핫 리로드는 하지 않음.

## 신뢰 모델 (가장 어려운 부분)

에이전트 import는 곧 타인의 코드 실행입니다. 기본값은 보수적으로:

| 위험 | 완화 |
|---|---|
| 악의적 `import` 부수효과 | 검증을 네트워크 차단 환경의 서브프로세스에서 실행; 호스트 프로세스는 미검증 코드를 절대 import하지 않음 |
| 의존성 혼동 / 타이포스쿼팅 | SDK 밴드 밖 의존성은 `--allow-deps` 필수; 락파일에 해시 고정 |
| 변조된 아카이브 | 선택적 `--sha256` 플래그; git import는 해석된 커밋 기록 |
| import된 에이전트의 권한 | 동일 프로세스 모델은 설계상 신뢰 기반 — 신뢰 불가 에이전트의 탈출구는 import가 아니라 별도 서비스 + A2A |

## 예시 저장소

공개 템플릿 저장소 `jyje/pilot-agent-template`를 만들어 git-import 데모 대상을 겸하게 합니다:

- 위 컨벤션이 미리 배선된 형태 (`cookiecutter` 스타일 플레이스홀더 또는 `create-agent` 스크립트)
- CI: `uv run pytest`(계약 하니스) + manifest JSON을 릴리스 아티팩트로 export (A2A 스타일 "agent card")
- 태그된 릴리스(`v0.1.0`)로 `agent-factory import git+...@v0.1.0`이 즉시 동작

## 마일스톤

1. **5a — 아카이브 import**: importer 모듈 + `import` CLI + 픽스처 zip 테스트 (정상/깨짐/비호환).
2. **5b — git import**: 클론 + ref 고정 + `agents.lock`.
3. **5c — 템플릿 저장소**: `pilot-agent-template` 공개, 엔드투엔드 데모 문서화 (`import git+…` → 웹앱 사이드바에 등장).
4. **5d (스트레치)** — `GET /api/agents`에 `agent.json` 호환 export 추가; 백엔드에 관리자 플래그로 보호된 `POST /api/import`.
