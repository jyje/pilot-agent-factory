"""Example sub-agent package: summarizer (two-node pipeline with custom state)."""

from typing import Any

from agent_factory_sdk import MESSAGES_SCHEMA, AgentManifest
from langchain_core.runnables import Runnable

_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        **MESSAGES_SCHEMA["properties"],
        "summary": {"type": "string", "description": "Prose summary of the input text"},
    },
    "required": ["messages", "summary"],
}


class SummarizerAgent:
    manifest = AgentManifest(
        name="summarizer",
        version="0.1.0",
        sdk_version="0.1.0",
        description="Summarizes long text into prose, then key bullet points",
        capabilities=["summarization", "text-processing"],
        output_schema=_OUTPUT_SCHEMA,
    )

    def build(self, config: dict[str, Any] | None = None) -> Runnable:
        from .graph import build_graph

        return build_graph(config)


AGENT = SummarizerAgent()

__all__ = ["AGENT", "SummarizerAgent"]
