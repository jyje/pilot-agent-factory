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

__version__ = SDK_VERSION

__all__ = [
    "AgentManifest",
    "AgentRegistry",
    "DROPIN_ATTR",
    "ENTRY_POINT_GROUP",
    "IncompatibleAgentError",
    "LoadError",
    "LoadReport",
    "MESSAGES_SCHEMA",
    "SDK_VERSION",
    "SubAgent",
    "check_compat",
    "load_dropin_agents",
    "load_installed_agents",
    "make_model",
    "resolve_llm",
]
