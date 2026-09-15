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
from langchain_core.messages import BaseMessage, SystemMessage
from pydantic import BaseModel

# Chat model integrations read API keys from process environment variables.
# pydantic-settings parsing .env in app/config.py does not automatically set
# os.environ, so load .env again at the point these integrations are built.
load_dotenv()

ModelTier = Literal["fast", "standard", "strong"]
SupportedProvider = Literal["anthropic"]
CallPurpose = Literal["generate", "evaluate"]


@dataclass(frozen=True)
class CallUsage:
    """Token counts for one model call, for cost and quality measurement."""

    purpose: CallPurpose
    tier: ModelTier
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0

    def as_dict(self) -> dict[str, object]:
        return {
            "purpose": self.purpose,
            "tier": self.tier,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_read_tokens": self.cache_read_tokens,
            "cache_creation_tokens": self.cache_creation_tokens,
        }


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


def _usage_from_message(
    message: object, *, purpose: CallPurpose, tier: ModelTier
) -> CallUsage:
    usage = getattr(message, "usage_metadata", None) or {}
    details = usage.get("input_token_details") or {}
    return CallUsage(
        purpose=purpose,
        tier=tier,
        input_tokens=usage.get("input_tokens", 0),
        output_tokens=usage.get("output_tokens", 0),
        cache_read_tokens=details.get("cache_read", 0),
        cache_creation_tokens=details.get("cache_creation", 0),
    )


def invoke_structured[T: BaseModel](
    *,
    schema: type[T],
    messages: list[BaseMessage],
    tier: ModelTier,
    model_config: GenerationModelConfig,
    purpose: CallPurpose,
    calls: list[CallUsage],
) -> T:
    """One structured-output call, with its token usage appended to `calls`.

    `include_raw=True` keeps the raw message, which carries usage_metadata.
    It also turns a parsing failure into a returned error instead of a
    raised one, so this re-raises it to keep the retry behavior in
    stage.py unchanged.
    """
    model = get_model(tier=tier, model_config=model_config)
    result = model.with_structured_output(schema, include_raw=True).invoke(messages)
    if not isinstance(result, dict):
        return result

    calls.append(_usage_from_message(result.get("raw"), purpose=purpose, tier=tier))
    parsed = result.get("parsed")
    if parsed is None:
        raise ValueError(
            f"Model did not return a valid {schema.__name__}: "
            f"{result.get('parsing_error')}"
        )
    return parsed
