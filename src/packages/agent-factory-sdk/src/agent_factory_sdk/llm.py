"""LLM construction helpers.

Mirrors the pilot-deepagents-rubrics convention: the Anthropic client is
pointed at LM Studio's Anthropic-compatible endpoint purely via env vars
(`ANTHROPIC_BASE_URL=http://127.0.0.1:1234`), so switching between BYOK and
local models never requires a code change.
"""

from __future__ import annotations

import os
from typing import Any

from langchain_core.language_models import BaseChatModel


def make_model(env_key: str = "MAIN_MODEL", default: str = "claude-sonnet-4-6") -> BaseChatModel:
    """Build a ChatAnthropic client from environment variables."""
    from langchain_anthropic import ChatAnthropic

    kwargs: dict[str, Any] = {
        "model": os.getenv(env_key, default),
        "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY"),
        "max_retries": 4,
    }
    if base_url := os.getenv("ANTHROPIC_BASE_URL"):
        kwargs["base_url"] = base_url
    return ChatAnthropic(**kwargs)


def resolve_llm(config: dict[str, Any] | None) -> BaseChatModel:
    """Return the injected `config["llm"]`, or build one from the environment.

    Every agent's `build()` should obtain its model through this helper so the
    host (and the SDK test harness) can inject clients.
    """
    if config and (llm := config.get("llm")) is not None:
        return llm
    return make_model()
