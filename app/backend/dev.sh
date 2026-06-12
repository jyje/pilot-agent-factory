#!/usr/bin/env bash
# Dev server launcher: frees port 8000 if occupied, then starts FastAPI with reload.
set -euo pipefail

PORT="${PORT:-8000}"

pid="$(lsof -ti tcp:"$PORT" || true)"
if [ -n "$pid" ]; then
    echo "Port $PORT is in use by PID $pid — killing it."
    kill -9 $pid
fi

exec uv run fastapi dev src/agent_factory_backend/server.py --port "$PORT"
