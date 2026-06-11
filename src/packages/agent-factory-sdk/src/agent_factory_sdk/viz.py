"""Graph structure rendering — Mermaid text for the platform and its agents."""

from __future__ import annotations

import re
from typing import Any

from langchain_core.runnables import Runnable

from .loader import AgentRegistry


def render_mermaid(runnable: Runnable) -> str:
    """Return the Mermaid flowchart for a compiled graph.

    Works for the deep supervisor, the Phase 4 supervisor, and individual
    sub-agent graphs alike — anything exposing LangGraph's `get_graph()`.
    """
    get_graph = getattr(runnable, "get_graph", None)
    if get_graph is None:
        raise TypeError(
            f"{type(runnable).__name__} has no get_graph(); pass a compiled LangGraph"
        )
    return get_graph().draw_mermaid()


def _node_id(prefix: str, name: str) -> str:
    return f"{prefix}_{re.sub(r'[^0-9a-zA-Z]', '_', name)}"


def render_platform_mermaid(
    registry: AgentRegistry, config: dict[str, Any] | None = None
) -> str:
    """One Mermaid picture of the whole platform.

    The deep supervisor at the top, each loaded agent's actual graph
    (nodes/edges from its compiled StateGraph) as a subgraph below it —
    so a newly imported agent shows up here without any drawing code.
    """
    lines = [
        "graph TD",
        '  supervisor{{"deep supervisor<br/>(task tool router)"}}',
    ]
    for name, agent in registry.agents.items():
        graph = agent.build(config).get_graph()
        prefix = re.sub(r"[^0-9a-zA-Z]", "_", name)
        lines.append(f'  subgraph sg_{prefix}["{name} v{agent.manifest.version}"]')
        for node in graph.nodes:
            lines.append(f'    {_node_id(prefix, node)}["{node}"]')
        for edge in graph.edges:
            arrow = "-.->" if edge.conditional else "-->"
            lines.append(
                f"    {_node_id(prefix, edge.source)} {arrow} {_node_id(prefix, edge.target)}"
            )
        lines.append("  end")
        lines.append(f"  supervisor -- task --> {_node_id(prefix, '__start__')}")
    return "\n".join(lines)
