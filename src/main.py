"""Host CLI: discover sub-agent packages at runtime and run them.

Usage:
    uv run python main.py list
    uv run python main.py run <agent> "<prompt>"
    uv run python main.py chat ["<prompt>"] [--simple]
    uv run python main.py graph [<agent>] [--top]

`list` shows agents from both load modes (installed entry points + dropins/),
including isolated load failures. `run` builds one chosen agent's graph.
`chat` assembles ALL loaded agents under the Phase 5 deep supervisor
(`--simple` falls back to the Phase 4 router); without a prompt it opens a
multi-turn REPL backed by an in-memory checkpointer. `graph` prints Mermaid:
the platform overview by default, one agent's graph, or the top-level graph.
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
        _print_message(msg)

    if summary := result.get("summary"):
        print(f"\n{BOLD}📝 summary channel{RESET}\n{summary}")
    print()
    return 0


def _print_message(msg) -> None:
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


def cmd_chat(args: argparse.Namespace) -> int:
    from agent_factory_sdk import build_deep_supervisor, build_supervisor
    from langgraph.checkpoint.memory import MemorySaver

    registry = discover()
    build = build_supervisor if args.simple else build_deep_supervisor
    graph = build(registry, checkpointer=MemorySaver())
    session = {"configurable": {"thread_id": "cli"}}

    mode = "supervisor (simple)" if args.simple else "deep supervisor"
    print(f"\n{BOLD}{mode}{RESET} over {len(registry.agents)} agents: "
          f"{', '.join(registry.agents)}")
    print("─" * 72)

    seen = {"routes": 0, "msgs": 0}

    def run_turn(prompt: str) -> None:
        seen["msgs"] += 1  # skip echoing the user's own message
        result: dict = {}
        for chunk in graph.stream(
            {"messages": [("user", prompt)]}, config=session, stream_mode="values"
        ):
            result = chunk
            for decision in chunk.get("route_trace", [])[seen["routes"]:]:
                print(f"\n{DIM}── supervisor → {BOLD}{decision['next']}{RESET}{DIM}"
                      f"  ({decision['reason']}) ──{RESET}")
                seen["routes"] += 1
            for msg in chunk.get("messages", [])[seen["msgs"]:]:
                _print_message(msg)
                seen["msgs"] += 1
        if artifacts := result.get("artifacts"):
            print(f"\n{BOLD}📦 artifacts{RESET}")
            for agent_name, extras in artifacts.items():
                for key, value in extras.items():
                    print(f"  {agent_name}.{key}: {str(value)[:200]}")

    if args.prompt:
        run_turn(args.prompt)
        print()
        return 0

    print(f"{DIM}multi-turn session (thread: cli) — exit/quit/Ctrl-D to leave{RESET}")
    while True:
        try:
            prompt = input(f"\n{BOLD}you>{RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if prompt.lower() in {"exit", "quit"}:
            break
        if prompt:
            run_turn(prompt)
    return 0


def cmd_graph(args: argparse.Namespace) -> int:
    from agent_factory_sdk import (
        build_deep_supervisor,
        render_mermaid,
        render_platform_mermaid,
    )

    registry = discover()
    if args.agent:
        try:
            print(render_mermaid(registry.get(args.agent).build()))
        except KeyError as e:
            print(f"{RED}error:{RESET} {e}", file=sys.stderr)
            return 1
    elif args.top:
        print(render_mermaid(build_deep_supervisor(registry)))
    else:
        print(render_platform_mermaid(registry))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="agent-factory host CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="list discovered agents and load failures")

    run = sub.add_parser("run", help="run one agent with a prompt")
    run.add_argument("agent", help="agent name (see `list`)")
    run.add_argument("prompt", help="user prompt")

    chat = sub.add_parser("chat", help="run the deep supervisor over all loaded agents")
    chat.add_argument("prompt", nargs="?", help="user prompt (omit for a multi-turn REPL)")
    chat.add_argument("--simple", action="store_true",
                      help="use the Phase 4 router instead of the deep agent")

    graph = sub.add_parser("graph", help="print Mermaid graph structure")
    graph.add_argument("agent", nargs="?", help="agent name for a single agent's graph")
    graph.add_argument("--top", action="store_true",
                       help="show the top-level deep agent graph instead of the overview")

    args = parser.parse_args()
    return {"list": cmd_list, "run": cmd_run, "chat": cmd_chat, "graph": cmd_graph}[
        args.command
    ](args)


if __name__ == "__main__":
    sys.exit(main())
