"""Host CLI: discover sub-agent packages at runtime and run them.

Usage:
    uv run python main.py list
    uv run python main.py run <agent> "<prompt>"

`list` shows agents from both load modes (installed entry points + dropins/),
including isolated load failures. `run` builds the chosen agent's graph and
streams it against the configured endpoint (LM Studio via .env).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from agent_factory_sdk import AgentRegistry  # noqa: E402

DROPIN_DIR = Path(__file__).parent / "dropins"

BOLD, DIM, GREEN, RED, YELLOW, RESET = (
    "\033[1m", "\033[2m", "\033[1;32m", "\033[1;31m", "\033[1;33m", "\033[0m",
)


def discover() -> AgentRegistry:
    return AgentRegistry().discover(dropin_dir=DROPIN_DIR)


def cmd_list(_: argparse.Namespace) -> int:
    registry = discover()

    print(f"\n{BOLD}Loaded agents{RESET} ({len(registry.agents)})")
    print("─" * 72)
    for manifest in registry.manifests():
        caps = ", ".join(manifest.capabilities)
        print(f"  {GREEN}●{RESET} {BOLD}{manifest.name:<12}{RESET} v{manifest.version}"
              f"  [sdk {manifest.sdk_version}]  {DIM}{caps}{RESET}")
        print(f"      {manifest.description}")

    if registry.errors:
        print(f"\n{BOLD}Load failures{RESET} ({len(registry.errors)}) — isolated, host still up")
        print("─" * 72)
        for err in registry.errors:
            print(f"  {RED}✗{RESET} {err.source}")
            print(f"      {DIM}{err.error}{RESET}")
    print()
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    registry = discover()
    try:
        agent = registry.get(args.agent)
    except KeyError as e:
        print(f"{RED}error:{RESET} {e}", file=sys.stderr)
        return 1

    manifest = agent.manifest
    print(f"\n{BOLD}{manifest.name}{RESET} v{manifest.version} — {manifest.description}")
    print("─" * 72)

    graph = agent.build()
    result: dict = {}
    for chunk in graph.stream({"messages": [("user", args.prompt)]}, stream_mode="values"):
        result = chunk

    for msg in result.get("messages", []):
        role = getattr(msg, "type", "?")
        style = {"human": "👤 Human", "ai": "🤖 AI", "tool": "🔧 Tool"}.get(role, role)
        print(f"\n{BOLD}{style}{RESET}")
        content = msg.content
        if isinstance(content, list):  # Anthropic block format
            content = "\n".join(
                b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"
            )
        if content:
            print(content)
        for tc in getattr(msg, "tool_calls", None) or []:
            print(f"  {YELLOW}⤷ call {tc['name']}({tc['args']}){RESET}")

    if summary := result.get("summary"):
        print(f"\n{BOLD}📝 summary channel{RESET}\n{summary}")
    print()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="agent-factory host CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="list discovered agents and load failures")

    run = sub.add_parser("run", help="run one agent with a prompt")
    run.add_argument("agent", help="agent name (see `list`)")
    run.add_argument("prompt", help="user prompt")

    args = parser.parse_args()
    return {"list": cmd_list, "run": cmd_run}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
