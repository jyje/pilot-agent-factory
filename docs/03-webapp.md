# Web App — Supervisor Console

> [한국어](03-webapp-ko.md)

![Agent Factory web app — calculator routed by the supervisor](assets/webapp-calculator.png)

The `app/` directory is the platform's **first external consumer**: a FastAPI backend and a Next.js frontend that depend on the `src/` packages the same way any other service would (path dependencies today, a private index in Phase 5).

```
app/
├── backend/    FastAPI — /api/agents, /api/chat (SSE)
└── frontend/   Next.js 16 + AI Elements + shadcn/ui
```

## Backend (`app/backend`)

```bash
cd app/backend
uv sync
uv run fastapi dev src/agent_factory_backend/server.py    # dev, auto-reload
# or: uv run uvicorn agent_factory_backend.server:app --port 8000
```

| Endpoint | Description |
|---|---|
| `GET /api/agents` | loaded manifests + isolated load failures (the Phase 3 registry, over HTTP) |
| `POST /api/chat` | runs the Phase 4 supervisor; streams SSE events `route` / `message` / `artifacts` / `done` / `error` |
| `/` | serves `app/frontend/dist` when a static export exists |

Environment resolution: local `.env` first, then falls back to `src/.env` (so the LM Studio setup is shared). Drop-in directory defaults to `src/dropins`, overridable via `AGENT_DROPINS`.

## Frontend (`app/frontend`)

```bash
cd app/frontend
pnpm install
pnpm dev        # http://localhost:3000 (expects backend on :8000)
```

`pnpm-workspace.yaml` pre-approves the two build scripts pnpm would otherwise block (`sharp`, `unrs-resolver`).

Component policy (per project convention):

- **AI Elements** for all conversational UI: `Conversation`, `Message`/`MessageResponse`, `PromptInput`, `Tool`, `ChainOfThought`.
- **shadcn/ui** for everything else: `Card`, `Badge`, `Separator`, `ScrollArea`.
- **`src/components/custom/`** wraps the two when our domain needs a shape they don't ship: `AgentCard`/`LoadErrorCard` (manifest + Phase 3 failures), `RouteStep` (supervisor decisions on ChainOfThought), `ToolCall` (our SSE tool events on the Tool part shape), `ArtifactsCard` (lifted state channels).
- `src/hooks/use-supervisor-chat.ts` parses the backend's SSE into a renderable timeline, pairing each AI tool call with its tool result.

`NEXT_PUBLIC_API_BASE` overrides the backend address (default `http://127.0.0.1:8000`).

### Note on vendored AI Elements

AI Elements components are vendored (shadcn model — you own the code). The installed shadcn generation uses **Base UI** primitives while some AI Elements code still expects the Radix API; the deltas are patched in place and marked with comments (hover-card delay props, two event handler types). Unused components were removed; re-add any with `npx ai-elements@latest add <name>`.
