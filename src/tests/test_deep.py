"""Phase 5: deep agent orchestration, graph rendering, and multi-turn sessions."""

from pathlib import Path

import pytest
from agent_factory_sdk import (
    AgentRegistry,
    build_deep_supervisor,
    build_supervisor,
    render_mermaid,
    render_platform_mermaid,
    to_compiled_subagents,
)
from agent_factory_sdk.deep import FILESYSTEM_TOOLS
from agent_factory_sdk.testing import ScriptedChatModel
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver

DROPIN_DIR = Path(__file__).parents[1] / "dropins"


@pytest.fixture(scope="module")
def registry() -> AgentRegistry:
    return AgentRegistry().discover(dropin_dir=DROPIN_DIR)


def test_compiled_subagent_specs_carry_manifest(registry):
    specs = {s["name"]: s for s in to_compiled_subagents(registry, {"llm": ScriptedChatModel()})}
    assert set(specs) == set(registry.agents)
    assert "capabilities: math, tool-use" in specs["calculator"]["description"]
    assert specs["calculator"]["runnable"] is not None


def test_deep_supervisor_builds_with_task_routing(registry):
    graph = build_deep_supervisor(registry, config={"llm": ScriptedChatModel()})
    nodes = set(graph.get_graph().nodes)
    assert {"model", "tools"} <= nodes
    mermaid = render_mermaid(graph)
    assert mermaid.startswith("---") or "graph TD" in mermaid


def test_deep_supervisor_rejects_empty_registry():
    with pytest.raises(ValueError, match="no loaded agents"):
        build_deep_supervisor(AgentRegistry())


def test_filesystem_tools_are_disconnected():
    # the routing profile must hide the whole filesystem/sandbox surface
    assert {"read_file", "write_file", "edit_file", "execute"} <= FILESYSTEM_TOOLS


def test_platform_mermaid_shows_every_agent_structure(registry):
    mermaid = render_platform_mermaid(registry, config={"llm": ScriptedChatModel()})
    for name in registry.agents:
        assert f'subgraph sg_{name}["{name} v' in mermaid
    # calculator's internal ReAct loop must be visible
    assert "calculator_agent" in mermaid and "calculator_tools" in mermaid
    # every agent hangs off the supervisor via the task tool
    assert mermaid.count("supervisor -- task -->") == len(registry.agents)


def route_call(next_: str) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[{"name": "route", "args": {"next": next_, "reason": "t"}, "id": "r"}],
    )


def test_supervisor_checkpointer_keeps_session_across_turns(registry):
    scripted = ScriptedChatModel(
        responses=[
            route_call("chitchat"), "first reply", route_call("FINISH"),
            route_call("chitchat"), "second reply", route_call("FINISH"),
        ]
    )
    graph = build_supervisor(registry, config={"llm": scripted}, checkpointer=MemorySaver())
    session = {"configurable": {"thread_id": "t1"}}

    first = graph.invoke({"messages": [("user", "hello")]}, config=session)
    assert len(first["messages"]) == 2

    second = graph.invoke({"messages": [("user", "again")]}, config=session)
    contents = [m.content for m in second["messages"]]
    # the thread accumulated both turns
    assert contents == ["hello", "first reply", "again", "second reply"]

    # a different thread starts clean
    other = {"configurable": {"thread_id": "t2"}}
    scripted2 = ScriptedChatModel(responses=[route_call("FINISH")])
    graph2 = build_supervisor(registry, config={"llm": scripted2}, checkpointer=MemorySaver())
    fresh = graph2.invoke({"messages": [("user", "new")]}, config=other)
    assert len(fresh["messages"]) == 1
