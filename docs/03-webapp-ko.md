# 웹앱 — 수퍼바이저 콘솔

> [English](03-webapp.md)

![Agent Factory 웹앱 — 수퍼바이저가 calculator로 라우팅](assets/webapp-calculator.png)

`app/` 디렉토리는 이 플랫폼의 **첫 외부 소비자**입니다: FastAPI 백엔드와 Next.js 프론트엔드가 다른 서비스와 동일한 방식으로 `src/` 패키지에 의존합니다 (현재는 path 의존성, Phase 5에서는 사설 인덱스).

```
app/
├── backend/    FastAPI — /api/agents, /api/chat (SSE)
└── frontend/   Next.js 16 + AI Elements + shadcn/ui
```

## 백엔드 (`app/backend`)

```bash
cd app/backend
uv sync
uv run fastapi dev src/agent_factory_backend/server.py    # 개발용, 자동 리로드
# 또는: uv run uvicorn agent_factory_backend.server:app --port 8000
```

| 엔드포인트 | 설명 |
|---|---|
| `GET /api/agents` | 로딩된 manifest + 격리된 로딩 실패 (Phase 3 레지스트리의 HTTP 노출) |
| `POST /api/chat` | Phase 4 수퍼바이저 실행; SSE 이벤트 `route` / `message` / `artifacts` / `done` / `error` 스트리밍 |
| `/` | 정적 빌드가 있으면 `app/frontend/dist` 서빙 |

환경변수 해석: 로컬 `.env` 우선, 없으면 `src/.env` 폴백 (LM Studio 설정 공유). 드롭인 디렉토리 기본값은 `src/dropins`, `AGENT_DROPINS`로 변경 가능.

## 프론트엔드 (`app/frontend`)

```bash
cd app/frontend
pnpm install
pnpm dev        # http://localhost:3000 (백엔드 :8000 필요)
```

`pnpm-workspace.yaml`이 pnpm이 차단하는 빌드 스크립트 2건(`sharp`, `unrs-resolver`)을 사전 승인합니다.

컴포넌트 정책 (프로젝트 컨벤션):

- **AI Elements**: 모든 대화형 UI — `Conversation`, `Message`/`MessageResponse`, `PromptInput`, `Tool`, `ChainOfThought`.
- **shadcn/ui**: 그 외 전부 — `Card`, `Badge`, `Separator`, `ScrollArea`.
- **`src/components/custom/`**: 우리 도메인에 필요한 형태가 없을 때 위 둘을 래핑 — `AgentCard`/`LoadErrorCard`(manifest + Phase 3 실패), `RouteStep`(ChainOfThought 위의 수퍼바이저 결정), `ToolCall`(SSE 툴 이벤트의 Tool part 매핑), `ArtifactsCard`(승격된 state 채널).
- `src/hooks/use-supervisor-chat.ts`: 백엔드 SSE를 렌더링 가능한 타임라인으로 파싱하고, AI 툴콜과 툴 결과를 쌍으로 묶습니다.

`NEXT_PUBLIC_API_BASE`로 백엔드 주소 변경 가능 (기본 `http://127.0.0.1:8000`).

### vendored AI Elements 참고

AI Elements 컴포넌트는 vendored 방식입니다 (shadcn 모델 — 코드를 우리가 소유). 설치된 shadcn 세대는 **Base UI** 프리미티브를 쓰는데 일부 AI Elements 코드가 아직 Radix API를 기대해서, 차이 나는 부분을 주석과 함께 제자리에서 패치했습니다 (hover-card delay props, 이벤트 핸들러 타입 2건). 미사용 컴포넌트는 제거했으며, 필요 시 `npx ai-elements@latest add <name>`으로 다시 추가하면 됩니다.
