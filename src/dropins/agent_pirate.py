"""Drop-in agent example (loader mode B).

This file is NOT pip-installed: the loader imports it straight from the
`dropins/` directory at runtime — the local equivalent of dropping a file
onto a mounted PVC/ConfigMap without rebuilding the image.
"""

from typing import Any

from agent_factory_sdk import AgentManifest, resolve_llm
from langchain_core.messages import SystemMessage
from langchain_core.runnables import Runnable
from langgraph.graph import END, START, MessagesState, StateGraph

SYSTEM_PROMPT = "You are a cheerful pirate. Answer every question in pirate speak, briefly."


class PirateAgent:
    manifest = AgentManifest(
        name="pirate",
        version="0.1.0",
        sdk_version="0.1.0",
        description="Answers everything in pirate speak (drop-in demo)",
        capabilities=["conversation", "novelty"],
    )

    def build(self, config: dict[str, Any] | None = None) -> Runnable:
        llm = resolve_llm(config)
        system = SystemMessage(content=SYSTEM_PROMPT)

        def chat(state: MessagesState) -> dict[str, Any]:
            return {"messages": [llm.invoke([system, *state["messages"]])]}

        builder = StateGraph(MessagesState)
        builder.add_node("chat", chat)
        builder.add_edge(START, "chat")
        builder.add_edge("chat", END)
        return builder.compile()


AGENT = PirateAgent()
