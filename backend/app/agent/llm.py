"""Model tiering and provider selection.

Cost is the top priority, then quality, then latency (generation runs in a
background job). Each provider gets its own model map for fast/standard/
strong tiers, and each generation run chooses one provider config.
"""

import os
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Literal

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI

# Chat model integrations read API keys from process environment variables.
# pydantic-settings parsing .env in app/config.py does not automatically set
# os.environ, so load .env again at the point these integrations are built.
load_dotenv()

ModelTier = Literal["fast", "standard", "strong"]
SupportedProvider = Literal[
    "anthropic",
    "openai",
    "groq",
    "xai",
    "mistral",
    "gemini",
    "ollama",
    "deepseek",
]


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
    "openai": {
        "fast": "gpt-4o-mini",
        "standard": "gpt-4o",
        "strong": "gpt-4.1",
    },
    "groq": {
        "fast": "llama-3.1-8b-instant",
        "standard": "llama-3.3-70b-versatile",
        "strong": "deepseek-r1-distill-llama-70b",
    },
    "xai": {
        "fast": "grok-3-mini",
        "standard": "grok-3",
        "strong": "grok-4",
    },
    "mistral": {
        "fast": "ministral-8b-latest",
        "standard": "mistral-small-latest",
        "strong": "mistral-large-latest",
    },
    "gemini": {
        "fast": "gemini-2.5-flash-lite",
        "standard": "gemini-2.5-flash",
        "strong": "gemini-2.5-pro",
    },
    "ollama": {
        "fast": "llama3.1:8b",
        "standard": "llama3.1:70b",
        "strong": "deepseek-r1:32b",
    },
    "deepseek": {
        "fast": "deepseek-chat",
        "standard": "deepseek-chat",
        "strong": "deepseek-reasoner",
    },
}

_PROVIDER_BASE_URLS: dict[SupportedProvider, str | None] = {
    "anthropic": None,
    "openai": None,
    "groq": "https://api.groq.com/openai/v1",
    "xai": "https://api.x.ai/v1",
    "mistral": "https://api.mistral.ai/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
    "ollama": "http://localhost:11434/v1",
    "deepseek": "https://api.deepseek.com/v1",
}

_PROVIDER_BASE_URL_ENV_VARS: dict[SupportedProvider, str] = {
    "anthropic": "ANTHROPIC_BASE_URL",
    "openai": "OPENAI_BASE_URL",
    "groq": "GROQ_BASE_URL",
    "xai": "XAI_BASE_URL",
    "mistral": "MISTRAL_BASE_URL",
    "gemini": "GEMINI_BASE_URL",
    "ollama": "OLLAMA_BASE_URL",
    "deepseek": "DEEPSEEK_BASE_URL",
}


def default_free_credit_model_config() -> GenerationModelConfig:
    # Free credits use the server-managed key path (currently Anthropic).
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
    if provider == "anthropic":
        kwargs: dict[str, object] = {"model_name": model_name, "max_retries": 2}
        if api_key:
            kwargs["api_key"] = api_key
        return ChatAnthropic(**kwargs)

    kwargs = {"model": model_name, "max_retries": 2}
    base_url = _provider_base_url_for(provider)
    if base_url:
        kwargs["base_url"] = base_url
    if api_key:
        kwargs["api_key"] = api_key
    elif provider == "ollama":
        # Ollama's OpenAI-compatible API is commonly unauthenticated.
        # ChatOpenAI still expects an api_key value, so provide a harmless
        # default token when no explicit key is set.
        kwargs["api_key"] = "ollama"
    return ChatOpenAI(**kwargs)


def _model_name_for(provider: SupportedProvider, tier: ModelTier) -> str:
    env_var = f"COURSE_GEN_MODEL_{provider.upper()}_{tier.upper()}"
    override = os.getenv(env_var)
    if override and override.strip():
        return override.strip()
    return _PROVIDER_TIER_MODELS[provider][tier]


def _provider_base_url_for(provider: SupportedProvider) -> str | None:
    env_var = _PROVIDER_BASE_URL_ENV_VARS[provider]
    override = os.getenv(env_var)
    if override and override.strip():
        return override.strip()
    return _PROVIDER_BASE_URLS[provider]


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
    """Provider-aware system message optimization.

    Anthropic supports explicit prompt-caching breakpoints. Other providers
    do not share that API shape, so they get a plain system message.
    """
    if provider == "anthropic":
        return SystemMessage(
            content=[
                {"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}
            ]
        )
    return SystemMessage(content=text)
