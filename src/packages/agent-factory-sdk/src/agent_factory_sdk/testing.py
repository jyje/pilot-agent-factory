"""Test harness for agent packages (Phase 1 deliverable).

`assert_agent_valid()` is the one-call CI gate every agent package should run
in its own test suite. `ScriptedChatModel` lets agent graphs execute end-to-end
without a real LLM endpoint.
"""

from __future__ import annotations

from typing import Any

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import Runnable
from pydantic import PrivateAttr

from .compat import check_compat
from .contract import AgentManifest, SubAgent


class ScriptedChatModel(BaseChatModel):
    """Fake chat model that replays a fixed list of responses.

    Sticks at the last response once the script is exhausted, and implements
    `bind_tools()` as a no-op so tool-calling agents can run under test.
    """

    # list[Any]: declaring AIMessage in the union trips langchain-core's
    # before-validator when pydantic probes the str branch
    responses: list[Any] = ["scripted response"]
    _index: int = PrivateAttr(default=0)

    @property
    def _llm_type(self) -> str:
        return "scripted-chat-model"

    def bind_tools(self, tools: Any, **kwargs: Any) -> Runnable:
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        raw = self.responses[min(self._index, len(self.responses) - 1)]
        self._index += 1
        message = AIMessage(content=raw) if isinstance(raw, str) else raw
        return ChatResult(generations=[ChatGeneration(message=message)])


def assert_agent_valid(agent: object, llm: BaseChatModel | None = None) -> SubAgent:
    """Validate an agent against the contract; returns it typed on success.

    Checks: protocol shape, manifest validity, SDK compatibility, and that
    `build()` returns a Runnable when given an injected (fake) LLM.
    """
    assert isinstance(agent, SubAgent), (
        f"{agent!r} does not satisfy the SubAgent protocol (needs `manifest` and `build()`)"
    )
    manifest = AgentManifest.model_validate(agent.manifest)
    check_compat(manifest)

    runnable = agent.build({"llm": llm or ScriptedChatModel()})
    assert isinstance(runnable, Runnable), (
        f"{manifest.name}.build() must return a Runnable, got {type(runnable).__name__}"
    )
    return agent
