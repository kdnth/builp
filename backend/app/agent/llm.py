"""Model tiering.

Cost is the top priority, then quality, then latency (this all runs as a
background job, so latency barely matters). That ordering is what drives
which tier each stage in graph.py uses:

  fast     claude-haiku-4-5    unit outlines (mechanical, derived straight
                                from the overview) and every evaluator call
                                (judging is a narrower task than writing).
  standard claude-sonnet-5     the course overview (one call per course, so
                                tier barely moves total cost) and lesson
                                content (the actual product surface).
  strong   claude-opus-5       never the default. Only used for the last
                                retry at a stage, as a quality backstop
                                without paying for it on the common path.
"""

from functools import lru_cache
from typing import Literal

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage

# ChatAnthropic reads ANTHROPIC_API_KEY from the process environment
# itself; pydantic-settings loading .env in app/config.py doesn't put it
# there. Loading it here too, at the actual point of need, means this
# module works whether or not app.config happened to be imported first.
load_dotenv()

ModelTier = Literal["fast", "standard", "strong"]

_TIER_MODELS: dict[ModelTier, str] = {
    "fast": "claude-haiku-4-5",
    "standard": "claude-sonnet-5",
    "strong": "claude-opus-5",
}


@lru_cache
def get_model(tier: ModelTier) -> ChatAnthropic:
    # No explicit temperature: current Claude models reject it as a
    # deprecated param (confirmed against the real API, not assumed).
    return ChatAnthropic(model=_TIER_MODELS[tier], max_retries=2)


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


def cached_system_message(text: str) -> SystemMessage:
    """A system message whose content is marked as an Anthropic cache breakpoint.

    Use this for the stable, reused context in a prompt (the course
    overview, a unit's outline) so sibling calls that share that prefix
    (other units, other lessons in the same unit) hit the cache instead of
    re-billing for it. Anthropic silently skips caching if the content is
    under its minimum cacheable size, so this is safe to apply unconditionally.
    """
    return SystemMessage(
        content=[{"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}]
    )
