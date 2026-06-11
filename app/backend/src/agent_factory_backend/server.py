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
import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Iterator

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

REPO_ROOT = Path(__file__).resolve().parents[4]
FRONTEND_DIST = REPO_ROOT / "app" / "frontend" / "dist"

# local .env first, then fall back to the platform's src/.env (LM Studio defaults)
load_dotenv()
load_dotenv(REPO_ROOT / "src" / ".env", override=False)

from agent_factory_sdk import (  # noqa: E402
    AgentRegistry,
    build_deep_supervisor,
    build_supervisor,
    render_mermaid,
    render_platform_mermaid,
)
from langchain_core.messages import AIMessageChunk  # noqa: E402
from langgraph.checkpoint.memory import MemorySaver  # noqa: E402

DROPIN_DIR = Path(os.getenv("AGENT_DROPINS", REPO_ROOT / "src" / "dropins"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    registry = AgentRegistry().discover(dropin_dir=DROPIN_DIR)
    app.state.registry = registry
    # deep agent on top (Phase 5); SUPERVISOR_MODE=simple falls back to the
    # Phase 4 router. The in-memory checkpointer keys sessions by thread_id.
    build = build_supervisor if os.getenv("SUPERVISOR_MODE") == "simple" else build_deep_supervisor
    app.state.supervisor = build(registry, checkpointer=MemorySaver())
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
    session_id: str = "default"


_THINK_RE = re.compile(r"<think(?:ing)?>(.*?)</think(?:ing)?>", re.DOTALL)
_REASONING_PREFIXES = (
    "thought process",
    "thinking process",
    "**thought process",
    "**thinking process",
    "here's a thinking process",
    "here is a thinking process",
    "my thinking process",
)


def _split_reasoning(text: str) -> tuple[str | None, str]:
    """Separate a model's thinking from its actual answer.

    Two shapes seen in the wild:
    - reasoning models that wrap thinking in <think>…</think> tags;
    - small local models (e.g. gemma) that narrate "Thought Process: …"
      inline and append the answer as the final paragraph.
    """
    if not text:
        return None, text
    if thinks := _THINK_RE.findall(text):
        answer = _THINK_RE.sub("", text).strip()
        return "\n\n".join(t.strip() for t in thinks), answer
    if text.lstrip().lower().startswith(_REASONING_PREFIXES):
        paragraphs = re.split(r"\n\s*\n", text.strip())
        if len(paragraphs) >= 2:
            return "\n\n".join(paragraphs[:-1]).strip(), paragraphs[-1].strip()
    return None, text


def _text_of(content: Any) -> str:
    if isinstance(content, list):  # Anthropic block format
        return "".join(
            b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"
        )
    return content or ""


def _serialize_message(msg: Any) -> dict[str, Any]:
    text = _text_of(msg.content).strip()
    if text == "[]":  # empty-reply artifact some local models emit
        text = ""
    reasoning, content = _split_reasoning(text)
    return {
        "role": getattr(msg, "type", "unknown"),
        "name": getattr(msg, "name", None),
        "content": content,
        "reasoning": reasoning,
        "tool_calls": [
            {"name": tc["name"], "args": tc["args"]}
            for tc in (getattr(msg, "tool_calls", None) or [])
        ],
    }


def _agent_of(meta: dict[str, Any]) -> str:
    """Attribute a streamed token to an agent via the trace metadata/tags
    set on every sub-agent runnable (make_adapter / to_compiled_subagents)."""
    if name := meta.get("agent_name"):
        return str(name)
    for tag in meta.get("tags") or []:
        if isinstance(tag, str) and tag.startswith("agent:"):
            return tag.removeprefix("agent:").split("@")[0]
    return "supervisor"


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
        # With a checkpointer, streamed values include the thread's full
        # history; the first chunk is the baseline (history + this turn's user
        # message) and only what grows past it is emitted.
        seen_routes: int | None = None
        seen_msgs: int | None = None
        answered = False
        try:
            # subgraphs=True is what surfaces sub-agent LLM tokens (they run
            # in nested graphs); their adapters tag them with agent_name.
            for ns, mode, payload in app.state.supervisor.stream(
                {"messages": [("user", request.message)]},
                config={"configurable": {"thread_id": request.session_id}},
                stream_mode=["messages", "values"],
                subgraphs=True,
            ):
                if mode == "messages":
                    chunk, meta = payload
                    if isinstance(chunk, AIMessageChunk) and (text := _text_of(chunk.content)):
                        yield sse("token", {"agent": _agent_of(meta), "text": text})
                    continue
                if ns:  # only top-level values carry the conversation state
                    continue

                result = payload
                routes = payload.get("route_trace", [])
                messages = payload.get("messages", [])
                if seen_msgs is None:
                    seen_routes, seen_msgs = len(routes), len(messages)
                    continue
                for decision in routes[seen_routes:]:
                    yield sse("route", decision)
                    seen_routes += 1
                for msg in messages[seen_msgs:]:
                    seen_msgs += 1
                    data = _serialize_message(msg)
                    if data["role"] == "ai" and not any(
                        (data["content"], data["reasoning"], data["tool_calls"])
                    ):
                        continue  # drop empty-reply artifacts entirely
                    if data["role"] == "ai" and data["content"]:
                        answered = True
                    yield sse("message", data)
            if not answered:
                yield sse(
                    "notice",
                    {"detail": "The model produced no answer this turn — try sending again."},
                )
            yield sse("artifacts", result.get("artifacts", {}))
            yield sse("done", {"session_id": request.session_id, "hops": result.get("hops", 0)})
        except Exception as e:  # noqa: BLE001 — surface to the client, don't kill the stream
            yield sse("error", {"detail": f"{type(e).__name__}: {e}"})

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/api/graph")
def platform_graph() -> dict[str, str]:
    """Mermaid overview: the supervisor plus every loaded agent's structure."""
    return {"scope": "platform", "mermaid": render_platform_mermaid(app.state.registry)}


@app.get("/api/graph/top")
def top_graph() -> dict[str, str]:
    """Mermaid for the top-level (deep) supervisor's own runtime graph."""
    return {"scope": "top", "mermaid": render_mermaid(app.state.supervisor)}


@app.get("/api/graph/{agent_name}")
def agent_graph(agent_name: str) -> dict[str, str]:
    """Mermaid for one loaded agent's compiled graph."""
    try:
        agent = app.state.registry.get(agent_name)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None
    return {"scope": agent_name, "mermaid": render_mermaid(agent.build())}


if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
