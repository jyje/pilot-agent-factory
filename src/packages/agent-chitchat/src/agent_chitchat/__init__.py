"""Example sub-agent package: chitchat (single-node conversation)."""

from typing import Any

from agent_factory_sdk import AgentManifest
from langchain_core.runnables import Runnable


class ChitchatAgent:
    manifest = AgentManifest(
        name="chitchat",
        version="0.1.0",
        sdk_version="0.1.0",
        description="General small-talk and Q&A in the user's language",
        capabilities=["conversation", "general-qa"],
    )

    def build(self, config: dict[str, Any] | None = None) -> Runnable:
        from .graph import build_graph

        return build_graph(config)


AGENT = ChitchatAgent()

__all__ = ["AGENT", "ChitchatAgent"]
