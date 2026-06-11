"""agent-factory-sdk — contract, loader, and test harness for LangGraph sub-agents."""

from .compat import IncompatibleAgentError, check_compat
from .contract import MESSAGES_SCHEMA, SDK_VERSION, AgentManifest, SubAgent
from .llm import make_model, resolve_llm
from .loader import (
    DROPIN_ATTR,
    ENTRY_POINT_GROUP,
    AgentRegistry,
    LoadError,
    LoadReport,
    load_dropin_agents,
    load_installed_agents,
)
from .deep import build_deep_supervisor, to_compiled_subagents
from .supervisor import (
    FINISH,
    SupervisorState,
    build_supervisor,
    make_adapter,
    make_router,
)
from .viz import render_mermaid, render_platform_mermaid

__version__ = SDK_VERSION

__all__ = [
    "AgentManifest",
    "AgentRegistry",
    "DROPIN_ATTR",
    "ENTRY_POINT_GROUP",
    "FINISH",
    "IncompatibleAgentError",
    "LoadError",
    "LoadReport",
    "MESSAGES_SCHEMA",
    "SDK_VERSION",
    "SubAgent",
    "SupervisorState",
    "build_deep_supervisor",
    "build_supervisor",
    "check_compat",
    "render_mermaid",
    "render_platform_mermaid",
    "to_compiled_subagents",
    "load_dropin_agents",
    "load_installed_agents",
    "make_adapter",
    "make_model",
    "make_router",
    "resolve_llm",
]
