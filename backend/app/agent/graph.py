"""The LangGraph workflow: overview -> units in parallel -> lessons in
parallel -> assemble.

Each fan-out step uses Command(update=..., goto=[Send(...), ...]) rather
than a separate conditional edge reading back the merged graph state.
Parallel Send-spawned branches in the same superstep aren't guaranteed to
see each other's writes until the superstep ends, so a unit's own node is
the only thing that decides that unit's own lessons: no risk of one
branch re-deriving (and duplicating) another branch's work.

The three generate_* functions are dependency-injected (default to the
real, LLM-backed versions in app.agent.nodes) so this module's fan-out,
convergence, and assembly logic can be tested with plain stub functions,
no model call or API key involved.
"""

import operator
from collections.abc import Callable, Mapping
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command, Send

from app.agent import nodes as default_nodes
from app.agent import prompts
from app.agent.assemble import assemble_course, assemble_lesson
from app.agent.budget import TokenBudget, job_token_budget
from app.agent.llm import GenerationModelConfig, default_free_credit_model_config
from app.agent.metrics import (
    MetricsReporter,
    NoopMetricsReporter,
    stage_metrics,
)
from app.agent.progress import NoopProgressReporter, ProgressReporter
from app.agent.schemas import (
    CourseOverview,
    LessonContent,
    LessonProfile,
    UnitOutline,
    UnitSummary,
)
from app.agent.stage import StageOutcome
from app.schemas.course import CodeLanguage, Course, CourseType, Lesson
from app.schemas.generation import (
    CodePracticeChoice,
    LearnerLevel,
    ReadingStyle,
)

OverviewFn = Callable[..., StageOutcome[CourseOverview]]
UnitOutlineFn = Callable[..., StageOutcome[UnitOutline]]
LessonContentFn = Callable[..., StageOutcome[LessonContent]]


class UnitOutlineRecord(TypedDict):
    unit_index: int
    unit: UnitSummary
    outline: UnitOutline
    passed: bool


class LessonRecord(TypedDict):
    unit_index: int
    lesson_index: int
    lesson: Lesson
    passed: bool


class GenerationState(TypedDict):
    topic: str
    audience: str
    num_units: int
    lessons_per_unit: int
    course_type: CourseType
    language: CodePracticeChoice
    level: LearnerLevel
    learning_goals: str | None
    notes: str | None
    reading_style: ReadingStyle
    model_config: GenerationModelConfig
    progress: ProgressReporter
    metrics: MetricsReporter
    budget: TokenBudget
    overview: CourseOverview
    overview_passed: bool
    unit_outlines: Annotated[list[UnitOutlineRecord], operator.add]
    lesson_records: Annotated[list[LessonRecord], operator.add]
    course: Course


def build_graph(
    *,
    overview_fn: OverviewFn = default_nodes.generate_overview,
    unit_outline_fn: UnitOutlineFn = default_nodes.generate_unit_outline,
    lesson_content_fn: LessonContentFn = default_nodes.generate_lesson_content,
    lesson_content_fns: Mapping[LessonProfile, LessonContentFn] | None = None,
) -> CompiledStateGraph:
    # Room for a specialized generator per profile without a graph change.
    by_profile: Mapping[LessonProfile, LessonContentFn] = lesson_content_fns or {}

    def node_generate_overview(state: GenerationState) -> Command:
        outcome = overview_fn(
            topic=state["topic"],
            audience=state["audience"],
            num_units=state["num_units"],
            course_type=state["course_type"],
            language=state["language"],
            level=state["level"],
            learning_goals=state["learning_goals"],
            notes=state["notes"],
            model_config=state["model_config"],
            budget=state["budget"],
        )
        state["metrics"].record_stage(stage_metrics("overview", outcome))
        state["progress"].stage("units")
        overview = outcome.content
        if len(overview.units) > state["num_units"]:
            overview = overview.model_copy(
                update={"units": overview.units[: state["num_units"]]}
            )
        return Command(
            update={"overview": overview, "overview_passed": outcome.passed},
            goto=[
                Send(
                    "generate_unit_outline",
                    {
                        "overview": overview,
                        "unit_index": index,
                        "unit": unit,
                        "lessons_per_unit": state["lessons_per_unit"],
                        "model_config": state["model_config"],
                        "progress": state["progress"],
                        "metrics": state["metrics"],
                        "budget": state["budget"],
                    },
                )
                for index, unit in enumerate(overview.units)
            ],
        )

    def node_generate_unit_outline(payload: dict) -> dict:
        outcome = unit_outline_fn(
            overview=payload["overview"],
            unit=payload["unit"],
            lessons_per_unit=payload["lessons_per_unit"],
            model_config=payload["model_config"],
            budget=payload["budget"],
        )
        payload["metrics"].record_stage(stage_metrics("unit_outline", outcome))
        outline = outcome.content
        lessons_per_unit = payload["lessons_per_unit"]
        if len(outline.lessons) > lessons_per_unit:
            outline = outline.model_copy(
                update={"lessons": outline.lessons[:lessons_per_unit]}
            )
        record: UnitOutlineRecord = {
            "unit_index": payload["unit_index"],
            "unit": payload["unit"],
            "outline": outline,
            "passed": outcome.passed,
        }
        return {"unit_outlines": [record]}

    def node_plan_lessons(state: GenerationState) -> Command:
        """Every lesson waits for every outline, so each lesson prompt can
        carry the whole course map. Without it, parallel lessons repeat each
        other and name the same idea differently."""
        overview = state["overview"]
        records = sorted(state["unit_outlines"], key=lambda r: r["unit_index"])
        outlines = [(record["unit"], record["outline"]) for record in records]

        progress = state["progress"]
        progress.set_lessons_total(sum(len(outline.lessons) for _, outline in outlines))
        progress.stage("lessons")

        return Command(
            goto=[
                Send(
                    "generate_lesson",
                    {
                        "overview": overview,
                        "unit": record["unit"],
                        "unit_index": record["unit_index"],
                        "outline": record["outline"],
                        "lesson_index": lesson_index,
                        "course_map": prompts.render_course_map(
                            overview,
                            outlines,
                            current=(record["unit_index"] + 1, lesson_index + 1),
                        ),
                        "reading_style": state["reading_style"],
                        "model_config": state["model_config"],
                        "progress": progress,
                        "metrics": state["metrics"],
                        "budget": state["budget"],
                    },
                )
                for record in records
                for lesson_index in range(len(record["outline"].lessons))
            ],
        )

    def node_generate_lesson(payload: dict) -> dict:
        lesson_summary = payload["outline"].lessons[payload["lesson_index"]]
        generate = by_profile.get(lesson_summary.profile, lesson_content_fn)
        outcome = generate(
            overview=payload["overview"],
            unit=payload["unit"],
            outline=payload["outline"],
            lesson_index=payload["lesson_index"],
            course_map=payload["course_map"],
            reading_style=payload["reading_style"],
            model_config=payload["model_config"],
            budget=payload["budget"],
        )
        payload["metrics"].record_stage(
            stage_metrics("lesson_content", outcome, profile=lesson_summary.profile)
        )
        policy = payload["overview"].brief.code_practice_policy
        code_language: CodeLanguage = policy if policy != "none" else "javascript"
        lesson = assemble_lesson(lesson_summary.title, outcome.content, code_language)
        payload["progress"].lesson_completed()
        record: LessonRecord = {
            "unit_index": payload["unit_index"],
            "lesson_index": payload["lesson_index"],
            "lesson": lesson,
            "passed": outcome.passed,
        }
        return {"lesson_records": [record]}

    def node_assemble(state: GenerationState) -> dict:
        state["progress"].stage("assembling")
        overview = state["overview"]
        by_unit: dict[int, list[LessonRecord]] = {
            index: [] for index in range(len(overview.units))
        }
        for record in state["lesson_records"]:
            by_unit[record["unit_index"]].append(record)

        unit_lessons: list[list[Lesson]] = []
        for index in range(len(overview.units)):
            ordered = sorted(by_unit[index], key=lambda r: r["lesson_index"])
            unit_lessons.append([r["lesson"] for r in ordered])

        course = assemble_course(overview, unit_lessons)
        return {"course": course}

    graph = StateGraph(GenerationState)
    graph.add_node("generate_overview", node_generate_overview)
    graph.add_node("generate_unit_outline", node_generate_unit_outline)
    graph.add_node("plan_lessons", node_plan_lessons)
    graph.add_node("generate_lesson", node_generate_lesson)
    graph.add_node("assemble", node_assemble)

    graph.add_edge(START, "generate_overview")
    graph.add_edge("generate_unit_outline", "plan_lessons")
    graph.add_edge("generate_lesson", "assemble")
    graph.add_edge("assemble", END)

    return graph.compile()


def run_generation(
    *,
    topic: str,
    audience: str,
    num_units: int,
    lessons_per_unit: int,
    course_type: CourseType = "programming",
    language: CodePracticeChoice = "javascript",
    level: LearnerLevel = "beginner",
    learning_goals: str | None = None,
    notes: str | None = None,
    reading_style: ReadingStyle = "single",
    model_config: GenerationModelConfig | None = None,
    progress: ProgressReporter | None = None,
    metrics: MetricsReporter | None = None,
    budget: TokenBudget | None = None,
    graph: CompiledStateGraph | None = None,
) -> Course:
    compiled = graph or build_graph()
    result = compiled.invoke(
        {
            "topic": topic,
            "audience": audience,
            "num_units": num_units,
            "lessons_per_unit": lessons_per_unit,
            "course_type": course_type,
            "language": language,
            "level": level,
            "learning_goals": learning_goals,
            "notes": notes,
            "reading_style": reading_style,
            "model_config": model_config or default_free_credit_model_config(),
            "progress": progress or NoopProgressReporter(),
            "metrics": metrics or NoopMetricsReporter(),
            "budget": budget
            or TokenBudget(job_token_budget(num_units, lessons_per_unit)),
            "unit_outlines": [],
            "lesson_records": [],
        }
    )
    return result["course"]
