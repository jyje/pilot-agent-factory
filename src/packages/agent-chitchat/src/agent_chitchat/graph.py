"""Single-node conversational graph — the minimal sub-agent shape."""

from __future__ import annotations

from typing import Any

from agent_factory_sdk import resolve_llm
from langchain_core.messages import SystemMessage
from langchain_core.runnables import Runnable
from langgraph.graph import END, START, MessagesState, StateGraph

SYSTEM_PROMPT = (
    "You are a friendly, concise conversational assistant. "
    "Answer in the same language the user writes in."
)


def build_graph(config: dict[str, Any] | None = None) -> Runnable:
    llm = resolve_llm(config)
    system = SystemMessage(content=SYSTEM_PROMPT)

    def chat(state: MessagesState) -> dict[str, Any]:
        return {"messages": [llm.invoke([system, *state["messages"]])]}

    builder = StateGraph(MessagesState)
    builder.add_node("chat", chat)
    builder.add_edge(START, "chat")
    builder.add_edge("chat", END)
    return builder.compile()
