"""Phase 2: every example agent passes the SDK harness and runs LLM-free."""

from pathlib import Path

import pytest
from agent_calculator import AGENT as calculator
from agent_chitchat import AGENT as chitchat
from agent_factory_sdk import load_dropin_agents
from agent_factory_sdk.testing import ScriptedChatModel, assert_agent_valid
from agent_summarizer import AGENT as summarizer
from langchain_core.messages import AIMessage

DROPIN_DIR = Path(__file__).parents[1] / "dropins"
pirate = load_dropin_agents(DROPIN_DIR).agents["pirate"]

ALL_AGENTS = [chitchat, calculator, summarizer, pirate]


@pytest.mark.parametrize("agent", ALL_AGENTS, ids=lambda a: a.manifest.name)
def test_agent_satisfies_contract(agent):
    assert_agent_valid(agent)


@pytest.mark.parametrize("agent", [chitchat, pirate], ids=lambda a: a.manifest.name)
def test_single_node_agents_reply(agent):
    graph = agent.build({"llm": ScriptedChatModel(responses=["hello there"])})
    result = graph.invoke({"messages": [("user", "hi")]})
    assert result["messages"][-1].content == "hello there"


def test_calculator_executes_tool_loop():
    scripted = ScriptedChatModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[{"name": "add", "args": {"a": 2, "b": 3}, "id": "call_1"}],
            ),
            AIMessage(content="2 + 3 = 5"),
        ]
    )
    graph = calculator.build({"llm": scripted})
    result = graph.invoke({"messages": [("user", "what is 2 + 3?")]})

    tool_messages = [m for m in result["messages"] if m.type == "tool"]
    assert tool_messages and tool_messages[0].content == "5.0"
    assert result["messages"][-1].content == "2 + 3 = 5"


def test_summarizer_fills_summary_channel():
    scripted = ScriptedChatModel(responses=["a prose summary", "- point one\n- point two"])
    graph = summarizer.build({"llm": scripted})
    result = graph.invoke({"messages": [("user", "long text " * 50)]})

    assert result["summary"] == "a prose summary"
    assert result["messages"][-1].content.startswith("- point one")


def test_manifest_capabilities_present_for_routing():
    for agent in ALL_AGENTS:
        assert agent.manifest.capabilities, f"{agent.manifest.name} has no routing hints"
