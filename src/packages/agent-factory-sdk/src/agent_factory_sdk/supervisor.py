"""Phase 4 — supervisor assembly.

Builds one executable multi-agent graph from whatever the registry loaded:

    __start__ → supervisor ─┬→ <agent A adapter> ─┐
                            ├→ <agent B adapter> ─┤→ back to supervisor
                            └→ FINISH → __end__   ┘

The same manifest serves three purposes here:
- `capabilities` + `description` → the router's roster prompt (routing)
- `output_schema`                → adapter knows which extra state channels
                                   to lift into `artifacts` (state mapping)
- `name` + `version`             → trace tags on every sub-agent run (observability)

Routing is a single `route` tool call (the tool-calling handoff style LangChain
recommends); sub-agents never see supervisor state and vice versa.
"""

from __future__ import annotations

import json
import operator
import re
from typing import Annotated, Any, Callable

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.runnables import Runnable
from langchain_core.tools import tool
from langgraph.graph import END, START, MessagesState, StateGraph

from .contract import SubAgent
from .llm import resolve_llm
from .loader import AgentRegistry

FINISH = "FINISH"
DEFAULT_MAX_HOPS = 6

SUPERVISOR_PROMPT = """You are a supervisor routing a user's request across specialized agents.

Available agents:
{roster}

Rules:
- Call the `route` tool with exactly one decision.
- `next` must be one of [{options}] or "{finish}".
- Pick "{finish}" when the conversation already contains a reply that fully answers the user's latest request.
- Do not pick the same agent twice in a row unless its last reply was clearly incomplete.
- Keep `reason` to one short sentence."""


def _merge_dicts(a: dict, b: dict) -> dict:
    return {**a, **b}


class SupervisorState(MessagesState):
    """Supervisor-level state. Sub-agents only ever see `messages`."""

    artifacts: Annotated[dict[str, dict[str, Any]], _merge_dicts]
    route_trace: Annotated[list[dict[str, str]], operator.add]
    hops: int
    next: str


@tool
def route(next: str, reason: str = "") -> str:
    """Select which agent acts next, or FINISH when the user's request is fully answered.

    Args:
        next: the name of one available agent, or "FINISH".
        reason: one short sentence explaining the choice.
    """
    return next


def _parse_decision(response: AIMessage, valid: set[str]) -> dict[str, str]:
    """Extract a routing decision, degrading gracefully for weak local models."""
    for tc in response.tool_calls or []:
        if tc["name"] == "route":
            nxt = str(tc["args"].get("next", FINISH)).strip()
            reason = str(tc["args"].get("reason", ""))
            if nxt in valid or nxt == FINISH:
                return {"next": nxt, "reason": reason}
            return {"next": FINISH, "reason": f"router chose unknown agent {nxt!r}"}

    text = response.text if isinstance(response.text, str) else response.text()
    if match := re.search(r"\{[^{}]*\"next\"[^{}]*\}", text or ""):
        try:
            data = json.loads(match.group())
            nxt = str(data.get("next", FINISH)).strip()
            if nxt in valid or nxt == FINISH:
                return {"next": nxt, "reason": str(data.get("reason", "parsed from text"))}
        except json.JSONDecodeError:
            pass

    # weak local models often answer in plain text instead of a tool call
    if FINISH in (text or ""):
        return {"next": FINISH, "reason": "finish stated in text"}

    return {"next": FINISH, "reason": "no usable route decision — finishing"}


def make_adapter(agent: SubAgent, config: dict[str, Any] | None = None) -> Callable:
    """Wrap a sub-agent graph as a supervisor node with state mapping.

    Input: only `messages` cross the boundary. Output: new messages are merged
    back, and any extra channels declared in the manifest's output_schema are
    lifted into `artifacts[<agent name>]`.
    """
    manifest = agent.manifest
    extra_keys = [k for k in manifest.output_schema.get("properties", {}) if k != "messages"]

    sub = agent.build(config).with_config(
        run_name=manifest.name,
        tags=[f"agent:{manifest.name}@{manifest.version}"],
        metadata={"agent_name": manifest.name, "agent_version": manifest.version},
    )

    def node(state: SupervisorState) -> dict[str, Any]:
        result = sub.invoke({"messages": state["messages"]})
        updates: dict[str, Any] = {
            "messages": result["messages"][len(state["messages"]):],
            "hops": state.get("hops", 0) + 1,
        }
        if extras := {k: result[k] for k in extra_keys if k in result}:
            updates["artifacts"] = {manifest.name: extras}
        return updates

    return node


def make_router(
    registry: AgentRegistry,
    config: dict[str, Any] | None = None,
    max_hops: int = DEFAULT_MAX_HOPS,
) -> Callable:
    """Build the supervisor node: an LLM that picks the next agent via the route tool."""
    manifests = registry.manifests()
    roster = "\n".join(
        f"- {m.name}: {m.description} (capabilities: {', '.join(m.capabilities) or 'n/a'})"
        for m in manifests
    )
    options = ", ".join(m.name for m in manifests)
    valid = set(registry.agents)
    base_prompt = SUPERVISOR_PROMPT.format(roster=roster, options=options, finish=FINISH)
    llm = resolve_llm(config).bind_tools([route])

    def supervisor(state: SupervisorState) -> dict[str, Any]:
        if state.get("hops", 0) >= max_hops:
            decision = {"next": FINISH, "reason": f"max hops ({max_hops}) reached"}
        else:
            prompt = base_prompt
            # weak local models tend to re-route to the agent that just replied;
            # surfacing their own routing history (inside the single system
            # message — Anthropic rejects non-consecutive system messages)
            # makes FINISH far more likely
            if consulted := [d["next"] for d in state.get("route_trace", []) if d["next"] != FINISH]:
                prompt += (
                    f"\n\nYou already consulted: {', '.join(consulted)} — their replies are in "
                    f'the conversation. If the user\'s request is now answered, call route with '
                    f'next="{FINISH}".'
                )
            response = llm.invoke([SystemMessage(content=prompt), *state["messages"]])
            decision = _parse_decision(response, valid)
        return {"next": decision["next"], "route_trace": [decision]}

    return supervisor


def build_supervisor(
    registry: AgentRegistry,
    config: dict[str, Any] | None = None,
    max_hops: int = DEFAULT_MAX_HOPS,
) -> Runnable:
    """Assemble the loaded agents into one supervised multi-agent graph."""
    if not registry.agents:
        raise ValueError("registry has no loaded agents — nothing to supervise")

    builder = StateGraph(SupervisorState)
    builder.add_node("supervisor", make_router(registry, config, max_hops))

    for name, agent in registry.agents.items():
        builder.add_node(name, make_adapter(agent, config))
        builder.add_edge(name, "supervisor")

    builder.add_edge(START, "supervisor")
    builder.add_conditional_edges(
        "supervisor",
        lambda state: state["next"],
        {name: name for name in registry.agents} | {FINISH: END},
    )
    return builder.compile()
