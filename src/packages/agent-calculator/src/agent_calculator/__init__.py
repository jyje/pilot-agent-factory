"""Example sub-agent package: calculator (ReAct tool loop)."""

from typing import Any

from agent_factory_sdk import AgentManifest
from langchain_core.runnables import Runnable


class CalculatorAgent:
    manifest = AgentManifest(
        name="calculator",
        version="0.1.0",
        sdk_version="0.1.0",
        description="Arithmetic via tool calls (add/subtract/multiply/divide)",
        capabilities=["math", "tool-use"],
    )

    def build(self, config: dict[str, Any] | None = None) -> Runnable:
        from .graph import build_graph

        return build_graph(config)


AGENT = CalculatorAgent()

__all__ = ["AGENT", "CalculatorAgent"]
