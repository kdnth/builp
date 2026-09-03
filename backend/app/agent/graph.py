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
from collections.abc import Callable
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command, Send

from app.agent import nodes as default_nodes
from app.agent.assemble import assemble_course, assemble_lesson
from app.agent.schemas import CourseOverview, LessonContent, UnitOutline, UnitSummary
from app.agent.stage import StageOutcome
from app.schemas.course import Course, Lesson

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
) -> CompiledStateGraph:
    def node_generate_overview(state: GenerationState) -> Command:
        outcome = overview_fn(
            topic=state["topic"],
            audience=state["audience"],
            num_units=state["num_units"],
        )
        overview = outcome.content
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
                    },
                )
                for index, unit in enumerate(overview.units)
            ],
        )

    def node_generate_unit_outline(payload: dict) -> Command:
        outcome = unit_outline_fn(
            overview=payload["overview"],
            unit=payload["unit"],
            lessons_per_unit=payload["lessons_per_unit"],
        )
        outline = outcome.content
        record: UnitOutlineRecord = {
            "unit_index": payload["unit_index"],
            "unit": payload["unit"],
            "outline": outline,
            "passed": outcome.passed,
        }
        return Command(
            update={"unit_outlines": [record]},
            goto=[
                Send(
                    "generate_lesson",
                    {
                        "overview": payload["overview"],
                        "unit": payload["unit"],
                        "unit_index": payload["unit_index"],
                        "outline": outline,
                        "lesson_index": lesson_index,
                    },
                )
                for lesson_index in range(len(outline.lessons))
            ],
        )

    def node_generate_lesson(payload: dict) -> dict:
        outcome = lesson_content_fn(
            overview=payload["overview"],
            unit=payload["unit"],
            outline=payload["outline"],
            lesson_index=payload["lesson_index"],
        )
        lesson_title = payload["outline"].lessons[payload["lesson_index"]].title
        lesson = assemble_lesson(lesson_title, outcome.content)
        record: LessonRecord = {
            "unit_index": payload["unit_index"],
            "lesson_index": payload["lesson_index"],
            "lesson": lesson,
            "passed": outcome.passed,
        }
        return {"lesson_records": [record]}

    def node_assemble(state: GenerationState) -> dict:
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
    graph.add_node("generate_lesson", node_generate_lesson)
    graph.add_node("assemble", node_assemble)

    graph.add_edge(START, "generate_overview")
    graph.add_edge("generate_lesson", "assemble")
    graph.add_edge("assemble", END)

    return graph.compile()


def run_generation(
    *,
    topic: str,
    audience: str,
    num_units: int,
    lessons_per_unit: int,
    graph: CompiledStateGraph | None = None,
) -> Course:
    compiled = graph or build_graph()
    result = compiled.invoke(
        {
            "topic": topic,
            "audience": audience,
            "num_units": num_units,
            "lessons_per_unit": lessons_per_unit,
            "unit_outlines": [],
            "lesson_records": [],
        }
    )
    return result["course"]
