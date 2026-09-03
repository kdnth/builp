"""Real, LLM-backed generate/evaluate closures for each stage.

Each function here wires app.agent.prompts and app.agent.llm around the
generic retry engine in app.agent.stage. graph.py depends on these three
functions by signature, not by name, so tests can swap in stub versions
and exercise the graph's fan-out/assembly structure with no model calls
and no API key.
"""

from app.agent import prompts
from app.agent.checks import (
    check_lesson_content,
    check_outline_lesson_count,
    check_overview_unit_count,
)
from app.agent.llm import GenerationModelConfig, ModelTier, get_model
from app.agent.schemas import (
    CourseOverview,
    EvaluationResult,
    LessonContent,
    UnitOutline,
    UnitSummary,
)
from app.agent.stage import StageOutcome, run_stage_with_retries

MAX_ATTEMPTS = 3


def generate_overview(
    *,
    topic: str,
    audience: str,
    num_units: int,
    model_config: GenerationModelConfig,
) -> StageOutcome[CourseOverview]:
    def generate(tier: ModelTier, feedback: str | None) -> CourseOverview:
        model = get_model(tier=tier, model_config=model_config).with_structured_output(
            CourseOverview
        )
        messages = prompts.overview_generate_prompt(
            topic=topic, audience=audience, num_units=num_units, feedback=feedback
        )
        return model.invoke(messages)  # type: ignore[return-value]

    def evaluate(overview: CourseOverview) -> EvaluationResult:
        model = get_model(
            tier="fast", model_config=model_config
        ).with_structured_output(EvaluationResult)
        return model.invoke(prompts.overview_evaluate_prompt(overview))  # type: ignore[return-value]

    return run_stage_with_retries(
        generate=generate,
        check=lambda overview: check_overview_unit_count(overview, num_units),
        evaluate=evaluate,
        default_tier="standard",
        max_attempts=MAX_ATTEMPTS,
    )


def generate_unit_outline(
    *,
    overview: CourseOverview,
    unit: UnitSummary,
    lessons_per_unit: int,
    model_config: GenerationModelConfig,
) -> StageOutcome[UnitOutline]:
    def generate(tier: ModelTier, feedback: str | None) -> UnitOutline:
        model = get_model(tier=tier, model_config=model_config).with_structured_output(
            UnitOutline
        )
        messages = prompts.unit_outline_generate_prompt(
            overview=overview,
            unit=unit,
            lessons_per_unit=lessons_per_unit,
            feedback=feedback,
            provider=model_config.provider,
        )
        return model.invoke(messages)  # type: ignore[return-value]

    def evaluate(outline: UnitOutline) -> EvaluationResult:
        model = get_model(
            tier="fast", model_config=model_config
        ).with_structured_output(EvaluationResult)
        messages = prompts.unit_outline_evaluate_prompt(
            overview=overview,
            unit=unit,
            outline=outline,
            provider=model_config.provider,
        )
        return model.invoke(messages)  # type: ignore[return-value]

    return run_stage_with_retries(
        generate=generate,
        check=lambda outline: check_outline_lesson_count(outline, lessons_per_unit),
        evaluate=evaluate,
        default_tier="fast",
        max_attempts=MAX_ATTEMPTS,
    )


def generate_lesson_content(
    *,
    overview: CourseOverview,
    unit: UnitSummary,
    outline: UnitOutline,
    lesson_index: int,
    model_config: GenerationModelConfig,
) -> StageOutcome[LessonContent]:
    def generate(tier: ModelTier, feedback: str | None) -> LessonContent:
        model = get_model(tier=tier, model_config=model_config).with_structured_output(
            LessonContent
        )
        messages = prompts.lesson_content_generate_prompt(
            overview=overview,
            unit=unit,
            outline=outline,
            lesson_index=lesson_index,
            feedback=feedback,
            provider=model_config.provider,
        )
        return model.invoke(messages)  # type: ignore[return-value]

    def evaluate(content: LessonContent) -> EvaluationResult:
        model = get_model(
            tier="fast", model_config=model_config
        ).with_structured_output(EvaluationResult)
        messages = prompts.lesson_content_evaluate_prompt(
            overview=overview,
            unit=unit,
            outline=outline,
            lesson_index=lesson_index,
            content=content,
            provider=model_config.provider,
        )
        return model.invoke(messages)  # type: ignore[return-value]

    return run_stage_with_retries(
        generate=generate,
        check=check_lesson_content,
        evaluate=evaluate,
        default_tier="standard",
        max_attempts=MAX_ATTEMPTS,
    )
