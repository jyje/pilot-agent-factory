"""FastAPI backend: the registry's `/agents` endpoint and a streaming chat API.

Endpoints:
- GET  /api/agents  — loaded manifests + isolated load failures (Phase 3)
- POST /api/chat    — run the Phase 4 supervisor, streaming SSE events:
                      route / message / artifacts / done / error
- /                 — serves the built Vue app (app/frontend/dist) if present

Run:
    cd app/backend
    uv sync
    uv run uvicorn agent_factory_backend.server:app --port 8000
"""

from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Iterator

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

REPO_ROOT = Path(__file__).resolve().parents[4]
FRONTEND_DIST = REPO_ROOT / "app" / "frontend" / "dist"

# local .env first, then fall back to the platform's src/.env (LM Studio defaults)
load_dotenv()
load_dotenv(REPO_ROOT / "src" / ".env", override=False)

from agent_factory_sdk import AgentRegistry, build_supervisor  # noqa: E402

DROPIN_DIR = Path(os.getenv("AGENT_DROPINS", REPO_ROOT / "src" / "dropins"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    registry = AgentRegistry().discover(dropin_dir=DROPIN_DIR)
    app.state.registry = registry
    app.state.supervisor = build_supervisor(registry)
    yield


app = FastAPI(title="agent-factory", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[  # Next.js dev server
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str


def _serialize_message(msg: Any) -> dict[str, Any]:
    content = msg.content
    if isinstance(content, list):  # Anthropic block format
        content = "\n".join(
            b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"
        )
    return {
        "role": getattr(msg, "type", "unknown"),
        "content": content or "",
        "tool_calls": [
            {"name": tc["name"], "args": tc["args"]}
            for tc in (getattr(msg, "tool_calls", None) or [])
        ],
    }


@app.get("/api/agents")
def list_agents() -> dict[str, Any]:
    registry: AgentRegistry = app.state.registry
    return {
        "agents": [m.model_dump() for m in registry.manifests()],
        "errors": [{"source": e.source, "error": e.error} for e in registry.errors],
    }


@app.post("/api/chat")
def chat(request: ChatRequest) -> StreamingResponse:
    def sse(event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    def stream() -> Iterator[str]:
        result: dict = {}
        seen_routes, seen_msgs = 0, 1  # skip echoing the user's own message
        try:
            for chunk in app.state.supervisor.stream(
                {"messages": [("user", request.message)]}, stream_mode="values"
            ):
                result = chunk
                for decision in chunk.get("route_trace", [])[seen_routes:]:
                    yield sse("route", decision)
                    seen_routes += 1
                for msg in chunk.get("messages", [])[seen_msgs:]:
                    yield sse("message", _serialize_message(msg))
                    seen_msgs += 1
            yield sse("artifacts", result.get("artifacts", {}))
            yield sse("done", {"hops": result.get("hops", 0)})
        except Exception as e:  # noqa: BLE001 — surface to the client, don't kill the stream
            yield sse("error", {"detail": f"{type(e).__name__}: {e}"})

    return StreamingResponse(stream(), media_type="text/event-stream")


if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
