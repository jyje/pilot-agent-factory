"""ReAct tool-loop graph: model ⇄ tools until no more tool calls."""

from __future__ import annotations

from typing import Any

from agent_factory_sdk import resolve_llm
from langchain_core.messages import SystemMessage
from langchain_core.runnables import Runnable
from langchain_core.tools import tool
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

SYSTEM_PROMPT = (
    "You are a precise calculator assistant. Use the provided tools for ALL "
    "arithmetic — never compute in your head. Show the final answer clearly."
)


@tool
def add(a: float, b: float) -> float:
    """Add two numbers."""
    return a + b


@tool
def subtract(a: float, b: float) -> float:
    """Subtract b from a."""
    return a - b


@tool
def multiply(a: float, b: float) -> float:
    """Multiply two numbers."""
    return a * b


@tool
def divide(a: float, b: float) -> float:
    """Divide a by b. b must not be zero."""
    if b == 0:
        raise ValueError("division by zero")
    return a / b


TOOLS = [add, subtract, multiply, divide]


def build_graph(config: dict[str, Any] | None = None) -> Runnable:
    llm = resolve_llm(config).bind_tools(TOOLS)
    system = SystemMessage(content=SYSTEM_PROMPT)

    def agent(state: MessagesState) -> dict[str, Any]:
        return {"messages": [llm.invoke([system, *state["messages"]])]}

    builder = StateGraph(MessagesState)
    builder.add_node("agent", agent)
    builder.add_node("tools", ToolNode(TOOLS))
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", tools_condition)
    builder.add_edge("tools", "agent")
    return builder.compile()
