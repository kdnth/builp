"""Real, LLM-backed generate/evaluate closures for each stage.

Each function here wires app.agent.prompts and app.agent.llm around the
generic retry engine in app.agent.stage. graph.py depends on these three
functions by signature, not by name, so tests can swap in stub versions
and exercise the graph's fan-out/assembly structure with no model calls
and no API key.
"""

from app.agent import prompts
from app.agent.budget import TokenBudget
from app.agent.checks import (
    check_lesson_content_split,
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
    GeneratedLessonActivityFix,
    GeneratedSection,
    LessonContent,
    UnitOutline,
    UnitSummary,
)
from app.agent.solver import solve_activities
from app.agent.stage import StageOutcome, run_stage_with_retries
from app.schemas.course import CourseType
from app.schemas.generation import CodePracticeChoice, LearnerLevel, ReadingStyle

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
    budget: TokenBudget | None = None,
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
            budget=budget,
        )

    def evaluate(overview: CourseOverview) -> EvaluationResult:
        return invoke_structured(
            schema=EvaluationResult,
            messages=prompts.overview_evaluate_prompt(overview, num_units=num_units),
            tier="fast",
            model_config=model_config,
            purpose="evaluate",
            calls=calls,
            budget=budget,
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
    budget: TokenBudget | None = None,
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
            budget=budget,
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
            budget=budget,
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


def _merge_activity_fix(
    draft: LessonContent, fix: GeneratedLessonActivityFix
) -> LessonContent:
    """Replace a section's activities with the fix's, matched by the
    section_index the model reported rather than by list position or
    count. Matching by position previously risked silently applying one
    section's fix to a different section whenever the model's response
    didn't cover every section in order - a real failure mode, found by
    testing against the 2026-09-22 golden-set analysis, that the
    deterministic checks do not catch (they validate an activity's own
    consistency, not which section it belongs in). An index the model
    didn't write for, or one outside the draft's range, keeps its
    section's original activities unchanged and is checked again on the
    next loop iteration like any other unresolved problem.
    """
    fixes_by_index = {
        entry.section_index: entry.activities
        for entry in fix.sections
        if 0 <= entry.section_index < len(draft.sections)
    }
    return LessonContent(
        sections=[
            GeneratedSection(
                title=section.title,
                markdown=section.markdown,
                activities=fixes_by_index.get(index, section.activities),
            )
            for index, section in enumerate(draft.sections)
        ],
        code_practice=draft.code_practice,
    )


def generate_lesson_content(
    *,
    overview: CourseOverview,
    unit: UnitSummary,
    outline: UnitOutline,
    lesson_index: int,
    course_map: str,
    reading_style: ReadingStyle,
    model_config: GenerationModelConfig,
    budget: TokenBudget | None = None,
) -> StageOutcome[LessonContent]:
    calls: list[CallUsage] = []
    last_draft: LessonContent | None = None
    activities_only_retry = False

    def generate(tier: ModelTier, feedback: str | None) -> LessonContent:
        if activities_only_retry and last_draft is not None and feedback:
            fix = invoke_structured(
                schema=GeneratedLessonActivityFix,
                messages=prompts.lesson_activities_fix_prompt(
                    overview=overview,
                    unit=unit,
                    outline=outline,
                    lesson_index=lesson_index,
                    course_map=course_map,
                    reading_style=reading_style,
                    draft=last_draft,
                    feedback=feedback,
                    provider=model_config.provider,
                ),
                tier=tier,
                model_config=model_config,
                purpose="generate_activities_fix",
                calls=calls,
                budget=budget,
            )
            return _merge_activity_fix(last_draft, fix)

        messages = prompts.lesson_content_generate_prompt(
            overview=overview,
            unit=unit,
            outline=outline,
            lesson_index=lesson_index,
            course_map=course_map,
            reading_style=reading_style,
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
            budget=budget,
        )

    def check(content: LessonContent) -> list[str]:
        nonlocal last_draft, activities_only_retry
        result = check_lesson_content_split(
            content, language=_lesson_code_language(overview, outline, lesson_index)
        )
        last_draft = content
        activities_only_retry = bool(result.activity) and not result.structural
        return result.combined

    def evaluate(content: LessonContent) -> EvaluationResult:
        nonlocal activities_only_retry
        ambiguity = solve_activities(
            content=content, model_config=model_config, calls=calls, budget=budget
        )
        if ambiguity:
            activities_only_retry = True
            return EvaluationResult(
                passed=False,
                score=2,
                feedback=(
                    "A reader who only had this lesson could not answer the "
                    "activities as written: " + "; ".join(ambiguity)
                ),
            )
        activities_only_retry = False

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
            budget=budget,
        )

    return run_stage_with_retries(
        generate=generate,
        check=check,
        evaluate=evaluate,
        default_tier="standard",
        max_attempts=MAX_ATTEMPTS,
        calls=calls,
    )
