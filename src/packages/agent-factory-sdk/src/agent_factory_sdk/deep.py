"""Phase 5 — deep agent orchestration.

Puts a LangChain deep agent at the top of the stack. Unlike the Phase 4
hand-rolled router, the deep agent plans with a todo list, delegates via the
`task` tool, and supports multi-turn sessions through a checkpointer — while
our runtime-loaded sub-agents plug in unchanged as `CompiledSubAgent`s.

Deliberate restrictions for this phase:
- the filesystem/sandbox surface is disconnected (no ls/read/write/edit/
  glob/grep/execute tools, no FilesystemMiddleware);
- the auto-added `general-purpose` subagent is disabled, so the ONLY route
  for real work is the registry's sub-agents.
"""

from __future__ import annotations

from typing import Any

from langchain_core.runnables import Runnable
from langgraph.checkpoint.base import BaseCheckpointSaver

from .contract import SubAgent
from .llm import resolve_llm
from .loader import AgentRegistry

#: built-in deep-agent tools we disconnect in this phase
FILESYSTEM_TOOLS = frozenset(
    {"ls", "read_file", "write_file", "edit_file", "glob", "grep", "execute"}
)

DEEP_SUPERVISOR_PROMPT = """You are a supervisor orchestrating specialized sub-agents.

Your ONLY way to do real work is delegating with the `task` tool — you have no
filesystem and must not answer domain questions yourself. Pick the sub-agent
whose description best matches the request, give it a clear instruction, and
relay its answer back to the user faithfully. If the user's request is already
fully answered by a sub-agent reply in this conversation, respond directly
without delegating again."""

_profile_registered = False


def _register_routing_profile() -> None:
    """Register a process-wide harness profile that strips the filesystem.

    deepagents resolves profiles per model provider; registering under
    "anthropic" covers every ChatAnthropic-built model in this process
    (including LM Studio behind the Anthropic-compatible endpoint).
    """
    global _profile_registered
    if _profile_registered:
        return
    from deepagents import (
        GeneralPurposeSubagentProfile,
        HarnessProfile,
        register_harness_profile,
    )

    # deepagents >=0.6.8 treats FilesystemMiddleware as required scaffolding,
    # so the filesystem is disconnected by hiding every one of its tools
    # rather than stripping the middleware itself.
    register_harness_profile(
        "anthropic",
        HarnessProfile(
            excluded_tools=FILESYSTEM_TOOLS,
            general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False),
        ),
    )
    _profile_registered = True


def to_compiled_subagents(
    registry: AgentRegistry, config: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    """Convert loaded registry agents into deepagents `CompiledSubAgent` specs.

    The manifest's description + capabilities become the delegation hint the
    deep agent sees on its `task` tool — the same fields the Phase 4 router
    used for its roster prompt.
    """

    def spec(agent: SubAgent) -> dict[str, Any]:
        m = agent.manifest
        caps = f" (capabilities: {', '.join(m.capabilities)})" if m.capabilities else ""
        return {
            "name": m.name,
            "description": f"{m.description}{caps}",
            "runnable": agent.build(config).with_config(
                run_name=m.name,
                tags=[f"agent:{m.name}@{m.version}"],
                metadata={"agent_name": m.name, "agent_version": m.version},
            ),
        }

    return [spec(agent) for agent in registry.agents.values()]


def build_deep_supervisor(
    registry: AgentRegistry,
    config: dict[str, Any] | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
) -> Runnable:
    """Assemble the loaded agents under a deep agent (Phase 5 top level).

    `checkpointer` enables multi-turn sessions: invoke with
    `config={"configurable": {"thread_id": <session id>}}` and the
    conversation state persists across calls.
    """
    if not registry.agents:
        raise ValueError("registry has no loaded agents — nothing to supervise")

    _register_routing_profile()
    from deepagents import create_deep_agent

    return create_deep_agent(
        model=resolve_llm(config),
        system_prompt=DEEP_SUPERVISOR_PROMPT,
        subagents=to_compiled_subagents(registry, config),
        checkpointer=checkpointer,
    )
