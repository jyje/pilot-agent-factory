"""Phase 1 — the agent contract.

Every sub-agent package implements `SubAgent`: a `manifest` describing the
agent, and a `build()` factory that returns a compiled LangGraph runnable.

Design rules:
- `build()` is a factory. Graphs must NOT be compiled at import time, so the
  host can inject an LLM client or override config per deployment.
- The default state contract is messages-in / messages-out (LangGraph
  `MessagesState`). Agents that need richer state declare it in
  `input_schema` / `output_schema`; the supervisor (Phase 4) uses these to
  generate state-mapping adapters.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from langchain_core.runnables import Runnable
from pydantic import BaseModel, Field

SDK_VERSION = "0.1.0"

#: JSON Schema for the default messages-in / messages-out contract.
MESSAGES_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "messages": {
            "type": "array",
            "items": {"type": "object"},
            "description": "LangChain message objects",
        }
    },
    "required": ["messages"],
}


class AgentManifest(BaseModel):
    """Static metadata shipped with every sub-agent package."""

    name: str = Field(
        pattern=r"^[a-z][a-z0-9_-]*$",
        description="Unique agent id (kebab/snake case)",
    )
    version: str = Field(
        pattern=r"^\d+\.\d+\.\d+$",
        description="Agent package version (semver)",
    )
    sdk_version: str = Field(
        pattern=r"^\d+\.\d+\.\d+$",
        description="agent-factory-sdk version this agent was built against",
    )
    description: str
    capabilities: list[str] = Field(
        default_factory=list,
        description="Routing hints for the supervisor (Phase 4)",
    )
    input_schema: dict[str, Any] = Field(default_factory=lambda: dict(MESSAGES_SCHEMA))
    output_schema: dict[str, Any] = Field(default_factory=lambda: dict(MESSAGES_SCHEMA))


@runtime_checkable
class SubAgent(Protocol):
    """Structural interface every sub-agent must satisfy.

    Implementations are plain classes — no inheritance from the SDK is
    required, which keeps agent packages decoupled from SDK internals.
    """

    manifest: AgentManifest

    def build(self, config: dict[str, Any] | None = None) -> Runnable:
        """Return a compiled StateGraph (or any Runnable).

        `config` keys recognized by convention:
        - "llm": a BaseChatModel instance to use instead of building one
          from environment variables (see `agent_factory_sdk.llm.resolve_llm`).
        """
        ...
