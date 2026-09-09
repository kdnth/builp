"""Model tiering for course generation.

Cost is the top priority, then quality, then latency (generation runs in a
background job). Anthropic is the only supported provider: it backs both
the server-managed free-credit path and the BYO-API-key path.
"""

import os
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Literal

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage

# Chat model integrations read API keys from process environment variables.
# pydantic-settings parsing .env in app/config.py does not automatically set
# os.environ, so load .env again at the point these integrations are built.
load_dotenv()

ModelTier = Literal["fast", "standard", "strong"]
SupportedProvider = Literal["anthropic"]


@dataclass(frozen=True)
class GenerationModelConfig:
    provider: SupportedProvider
    api_key: str | None = field(default=None, repr=False)


_PROVIDER_TIER_MODELS: dict[SupportedProvider, dict[ModelTier, str]] = {
    "anthropic": {
        "fast": "claude-haiku-4-5",
        "standard": "claude-sonnet-5",
        "strong": "claude-opus-5",
    },
}


def default_free_credit_model_config() -> GenerationModelConfig:
    # Free credits use the server-managed key path (Anthropic).
    return GenerationModelConfig(provider="anthropic")


@lru_cache
def _get_cached_model(provider: SupportedProvider, tier: ModelTier) -> BaseChatModel:
    return _build_model(provider=provider, tier=tier, api_key=None)


def get_model(*, tier: ModelTier, model_config: GenerationModelConfig) -> BaseChatModel:
    # Never cache user-provided API key models: cache entries would retain
    # those keys beyond a single request, violating ephemeral-key handling.
    if model_config.api_key is None:
        return _get_cached_model(model_config.provider, tier)
    return _build_model(
        provider=model_config.provider, tier=tier, api_key=model_config.api_key
    )


def _build_model(
    *, provider: SupportedProvider, tier: ModelTier, api_key: str | None
) -> BaseChatModel:
    model_name = _model_name_for(provider, tier)
    kwargs: dict[str, object] = {"model_name": model_name, "max_retries": 2}
    if api_key:
        kwargs["api_key"] = api_key
    return ChatAnthropic(**kwargs)


def _model_name_for(provider: SupportedProvider, tier: ModelTier) -> str:
    env_var = f"COURSE_GEN_MODEL_{provider.upper()}_{tier.upper()}"
    override = os.getenv(env_var)
    if override and override.strip():
        return override.strip()
    return _PROVIDER_TIER_MODELS[provider][tier]


def tier_for_attempt(
    default_tier: ModelTier, attempt: int, max_attempts: int
) -> ModelTier:
    """Which tier to generate with on a given attempt (1-indexed).

    Every attempt but the last uses the stage's normal tier. The last
    attempt (the one that must not fail, since there's no retry left after
    it) escalates to `strong` as a quality backstop. This keeps `strong`
    off the common path entirely.
    """
    if attempt >= max_attempts and default_tier != "strong":
        return "strong"
    return default_tier


def cached_system_message(text: str, *, provider: SupportedProvider) -> SystemMessage:
    """Anthropic supports explicit prompt-caching breakpoints."""
    return SystemMessage(
        content=[
            {"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}
        ]
    )
