"""The first step of a job: decide whether this app should teach the topic.

One fast-tier call, before any expensive work. Study is not harm, so the
line is between teaching a subject and helping someone do damage or giving
one person professional advice.
"""

from app.agent import prompts
from app.agent.budget import TokenBudget
from app.agent.llm import CallUsage, GenerationModelConfig, invoke_structured
from app.agent.schemas import ScreeningDecision


def screen_topic(
    *,
    topic: str,
    audience: str,
    learning_goals: str | None,
    notes: str | None,
    model_config: GenerationModelConfig,
    calls: list[CallUsage],
    budget: TokenBudget | None = None,
) -> ScreeningDecision:
    return invoke_structured(
        schema=ScreeningDecision,
        messages=prompts.screening_prompt(
            topic=topic,
            audience=audience,
            learning_goals=learning_goals,
            notes=notes,
        ),
        tier="fast",
        model_config=model_config,
        purpose="screen",
        calls=calls,
        budget=budget,
    )
