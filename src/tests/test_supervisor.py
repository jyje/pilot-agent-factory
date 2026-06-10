"""Phase 4: supervisor assembly — routing, adapters, artifacts, termination."""

from pathlib import Path

import pytest
from agent_factory_sdk import AgentRegistry, build_supervisor
from agent_factory_sdk.supervisor import _parse_decision
from agent_factory_sdk.testing import ScriptedChatModel
from langchain_core.messages import AIMessage

DROPIN_DIR = Path(__file__).parents[1] / "dropins"


@pytest.fixture(scope="module")
def registry() -> AgentRegistry:
    return AgentRegistry().discover(dropin_dir=DROPIN_DIR)


def route_call(next_: str, reason: str = "test") -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[{"name": "route", "args": {"next": next_, "reason": reason}, "id": "r1"}],
    )


def test_routes_to_agent_then_finishes(registry):
    # call order: router → chitchat's llm → router
    scripted = ScriptedChatModel(
        responses=[route_call("chitchat"), "hello from chitchat", route_call("FINISH", "answered")]
    )
    graph = build_supervisor(registry, config={"llm": scripted})
    result = graph.invoke({"messages": [("user", "hi")]})

    assert result["messages"][-1].content == "hello from chitchat"
    assert [d["next"] for d in result["route_trace"]] == ["chitchat", "FINISH"]
    assert result["hops"] == 1


def test_artifacts_lifted_from_output_schema(registry):
    # call order: router → summarize → keypoints → router
    scripted = ScriptedChatModel(
        responses=[
            route_call("summarizer"),
            "a prose summary",
            "- p1\n- p2",
            route_call("FINISH"),
        ]
    )
    graph = build_supervisor(registry, config={"llm": scripted})
    result = graph.invoke({"messages": [("user", "summarize this " * 20)]})

    assert result["artifacts"]["summarizer"]["summary"] == "a prose summary"
    assert result["messages"][-1].content.startswith("- p1")


def test_max_hops_terminates_loop(registry):
    # router keeps choosing chitchat; max_hops must cut the loop without an LLM call
    responses = [route_call("chitchat"), "reply", route_call("chitchat"), "reply again"]
    scripted = ScriptedChatModel(responses=responses)
    graph = build_supervisor(registry, config={"llm": scripted}, max_hops=2)
    result = graph.invoke({"messages": [("user", "loop forever")]})

    assert result["hops"] == 2
    assert result["route_trace"][-1]["next"] == "FINISH"
    assert "max hops" in result["route_trace"][-1]["reason"]


def test_unknown_route_degrades_to_finish(registry):
    scripted = ScriptedChatModel(responses=[route_call("does-not-exist")])
    graph = build_supervisor(registry, config={"llm": scripted})
    result = graph.invoke({"messages": [("user", "hi")]})

    assert result["route_trace"] == [
        {"next": "FINISH", "reason": "router chose unknown agent 'does-not-exist'"}
    ]
    assert result.get("hops", 0) == 0


def test_parse_decision_json_fallback():
    response = AIMessage(content='I will pick {"next": "calculator", "reason": "math"} now.')
    decision = _parse_decision(response, {"calculator"})
    assert decision == {"next": "calculator", "reason": "math"}


def test_parse_decision_garbage_finishes():
    decision = _parse_decision(AIMessage(content="no idea what to do"), {"calculator"})
    assert decision["next"] == "FINISH"


def test_empty_registry_rejected():
    with pytest.raises(ValueError, match="no loaded agents"):
        build_supervisor(AgentRegistry())
