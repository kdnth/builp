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
    check_outline_lessons,
    check_overview_unit_count,
)
from app.agent.llm import (
    CallUsage,
    GenerationModelConfig,
    ModelTier,
    invoke_structured,
)
from app.agent.schemas import (
    CodePracticePolicy,
    CourseOverview,
    EvaluationResult,
    LessonContent,
    UnitOutline,
    UnitSummary,
)
from app.agent.solver import solve_activities
from app.agent.stage import StageOutcome, run_stage_with_retries
from app.schemas.course import CourseType
from app.schemas.generation import CodePracticeChoice, LearnerLevel

MAX_ATTEMPTS = 3


def generate_overview(
    *,
    topic: str,
    audience: str,
    num_units: int,
    course_type: CourseType,
    language: CodePracticeChoice,
    level: LearnerLevel,
    learning_goals: str | None,
    notes: str | None,
    model_config: GenerationModelConfig,
) -> StageOutcome[CourseOverview]:
    calls: list[CallUsage] = []

    def generate(tier: ModelTier, feedback: str | None) -> CourseOverview:
        messages = prompts.overview_generate_prompt(
            topic=topic,
            audience=audience,
            num_units=num_units,
            course_type=course_type,
            language=language,
            level=level,
            learning_goals=learning_goals,
            notes=notes,
            feedback=feedback,
        )
        return invoke_structured(
            schema=CourseOverview,
            messages=messages,
            tier=tier,
            model_config=model_config,
            purpose="generate",
            calls=calls,
        )

    def evaluate(overview: CourseOverview) -> EvaluationResult:
        return invoke_structured(
            schema=EvaluationResult,
            messages=prompts.overview_evaluate_prompt(overview),
            tier="fast",
            model_config=model_config,
            purpose="evaluate",
            calls=calls,
        )

    return run_stage_with_retries(
        generate=generate,
        check=lambda overview: check_overview_unit_count(overview, num_units),
        evaluate=evaluate,
        default_tier="standard",
        max_attempts=MAX_ATTEMPTS,
        calls=calls,
    )


def generate_unit_outline(
    *,
    overview: CourseOverview,
    unit: UnitSummary,
    lessons_per_unit: int,
    model_config: GenerationModelConfig,
) -> StageOutcome[UnitOutline]:
    calls: list[CallUsage] = []

    def generate(tier: ModelTier, feedback: str | None) -> UnitOutline:
        messages = prompts.unit_outline_generate_prompt(
            overview=overview,
            unit=unit,
            lessons_per_unit=lessons_per_unit,
            feedback=feedback,
            provider=model_config.provider,
        )
        return invoke_structured(
            schema=UnitOutline,
            messages=messages,
            tier=tier,
            model_config=model_config,
            purpose="generate",
            calls=calls,
        )

    def evaluate(outline: UnitOutline) -> EvaluationResult:
        messages = prompts.unit_outline_evaluate_prompt(
            overview=overview,
            unit=unit,
            outline=outline,
            provider=model_config.provider,
        )
        return invoke_structured(
            schema=EvaluationResult,
            messages=messages,
            tier="fast",
            model_config=model_config,
            purpose="evaluate",
            calls=calls,
        )

    return run_stage_with_retries(
        generate=generate,
        check=lambda outline: (
            check_outline_lesson_count(outline, lessons_per_unit)
            + check_outline_lessons(outline, overview.brief)
        ),
        evaluate=evaluate,
        default_tier="fast",
        max_attempts=MAX_ATTEMPTS,
        calls=calls,
    )


def _lesson_code_language(
    overview: CourseOverview, outline: UnitOutline, lesson_index: int
) -> CodePracticePolicy:
    """The language this lesson's code practice uses, or "none" when the
    lesson should have no code practice at all."""
    if not outline.lessons[lesson_index].include_code_practice:
        return "none"
    return overview.brief.code_practice_policy


def generate_lesson_content(
    *,
    overview: CourseOverview,
    unit: UnitSummary,
    outline: UnitOutline,
    lesson_index: int,
    course_map: str,
    model_config: GenerationModelConfig,
) -> StageOutcome[LessonContent]:
    calls: list[CallUsage] = []

    def generate(tier: ModelTier, feedback: str | None) -> LessonContent:
        messages = prompts.lesson_content_generate_prompt(
            overview=overview,
            unit=unit,
            outline=outline,
            lesson_index=lesson_index,
            course_map=course_map,
            feedback=feedback,
            provider=model_config.provider,
        )
        return invoke_structured(
            schema=LessonContent,
            messages=messages,
            tier=tier,
            model_config=model_config,
            purpose="generate",
            calls=calls,
        )

    def evaluate(content: LessonContent) -> EvaluationResult:
        ambiguity = solve_activities(
            content=content, model_config=model_config, calls=calls
        )
        if ambiguity:
            return EvaluationResult(
                passed=False,
                score=2,
                feedback=(
                    "A reader who only had this lesson could not answer the "
                    "activities as written: " + "; ".join(ambiguity)
                ),
            )

        messages = prompts.lesson_content_evaluate_prompt(
            overview=overview,
            unit=unit,
            outline=outline,
            lesson_index=lesson_index,
            content=content,
            provider=model_config.provider,
        )
        return invoke_structured(
            schema=EvaluationResult,
            messages=messages,
            tier="fast",
            model_config=model_config,
            purpose="evaluate",
            calls=calls,
        )

    return run_stage_with_retries(
        generate=generate,
        check=lambda content: check_lesson_content(
            content, language=_lesson_code_language(overview, outline, lesson_index)
        ),
        evaluate=evaluate,
        default_tier="standard",
        max_attempts=MAX_ATTEMPTS,
        calls=calls,
    )
