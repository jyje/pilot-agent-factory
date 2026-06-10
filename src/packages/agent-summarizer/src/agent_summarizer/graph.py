"""Two-node pipeline: draft a prose summary, then distill key points.

Demonstrates an agent with custom state beyond plain messages; the extra
`summary` channel is declared in the manifest's output_schema.
"""

from __future__ import annotations

from typing import Any

from agent_factory_sdk import resolve_llm
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import Runnable
from langgraph.graph import END, START, MessagesState, StateGraph

SUMMARIZE_PROMPT = (
    "Summarize the user's text in 2-3 plain sentences. "
    "Keep the language of the original text."
)
KEYPOINTS_PROMPT = (
    "Rewrite the following summary as 3-5 concise bullet points. "
    "Output only the bullet list."
)


class SummarizerState(MessagesState):
    summary: str


def _text(message: Any) -> str:
    # BaseMessage.text is a method in langchain-core 0.3 and a property in 1.x
    text = message.text
    return text if isinstance(text, str) else text()


def build_graph(config: dict[str, Any] | None = None) -> Runnable:
    llm = resolve_llm(config)

    def summarize(state: SummarizerState) -> dict[str, Any]:
        response = llm.invoke([SystemMessage(content=SUMMARIZE_PROMPT), *state["messages"]])
        return {"summary": _text(response)}

    def keypoints(state: SummarizerState) -> dict[str, Any]:
        response = llm.invoke(
            [SystemMessage(content=KEYPOINTS_PROMPT), HumanMessage(content=state["summary"])]
        )
        return {"messages": [response]}

    builder = StateGraph(SummarizerState)
    builder.add_node("summarize", summarize)
    builder.add_node("keypoints", keypoints)
    builder.add_edge(START, "summarize")
    builder.add_edge("summarize", "keypoints")
    builder.add_edge("keypoints", END)
    return builder.compile()
