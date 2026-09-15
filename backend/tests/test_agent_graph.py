from app.agent.graph import build_graph, run_generation
from app.agent.schemas import (
    CourseOverview,
    GeneratedFunctionPractice,
    GeneratedMultipleChoiceActivity,
    GeneratedTestCase,
    LessonContent,
    LessonSummary,
    UnitOutline,
    UnitSummary,
)
from app.agent.stage import StageOutcome


def _passing_overview(*, topic, audience, num_units, language, model_config):
    overview = CourseOverview(
        title=f"Learn {topic}",
        description="A course.",
        audience=audience,
        units=[
            UnitSummary(title=f"Unit {i + 1}", goal=f"Cover part {i + 1}.")
            for i in range(num_units)
        ],
    )
    return StageOutcome(content=overview, passed=True, attempts=[])


def _passing_unit_outline(*, overview, unit, lessons_per_unit, language, model_config):
    outline = UnitOutline(
        lessons=[
            LessonSummary(
                title=f"{unit.title} Lesson {i + 1}",
                goal="Learn a thing.",
                include_code_practice=False,
                interactive_activity_types=["multipleChoice"],
            )
            for i in range(lessons_per_unit)
        ]
    )
    return StageOutcome(content=outline, passed=True, attempts=[])


def _passing_lesson_content(
    *, overview, unit, outline, lesson_index, language, model_config
):
    content = LessonContent(
        written_lesson_markdown=f"# {outline.lessons[lesson_index].title}",
        code_practice=None,
        interactive_activities=[
            GeneratedMultipleChoiceActivity(
                question="Is this a test?", options=["Yes", "No"], correct_index=0
            )
        ],
    )
    return StageOutcome(content=content, passed=True, attempts=[])


def test_graph_produces_a_fully_assembled_course():
    graph = build_graph(
        overview_fn=_passing_overview,
        unit_outline_fn=_passing_unit_outline,
        lesson_content_fn=_passing_lesson_content,
    )

    course = run_generation(
        topic="testing",
        audience="beginners",
        num_units=3,
        lessons_per_unit=2,
        graph=graph,
    )

    assert course.title == "Learn testing"
    assert len(course.units) == 3
    for unit in course.units:
        assert len(unit.lessons) == 2

    # every lesson got its own unique id and title, in the right order,
    # and every id in the whole document is unique (no unit/lesson mixing
    # between parallel branches)
    all_ids = [course.id]
    for unit_index, unit in enumerate(course.units, start=1):
        all_ids.append(unit.id)
        for lesson_index, lesson in enumerate(unit.lessons, start=1):
            all_ids.append(lesson.id)
            assert lesson.title == f"Unit {unit_index} Lesson {lesson_index}"

    assert len(all_ids) == len(set(all_ids))


def test_graph_result_validates_against_the_real_course_schema():
    from app.schemas.course import Course

    graph = build_graph(
        overview_fn=_passing_overview,
        unit_outline_fn=_passing_unit_outline,
        lesson_content_fn=_passing_lesson_content,
    )
    course = run_generation(
        topic="testing",
        audience="beginners",
        num_units=2,
        lessons_per_unit=1,
        graph=graph,
    )
    Course.model_validate(course.model_dump())


def test_graph_handles_uneven_lesson_counts_per_unit():
    def variable_unit_outline(
        *, overview, unit, lessons_per_unit, language, model_config
    ):
        # unit N gets N lessons, not a fixed count
        count = int(unit.title.split()[-1])
        outline = UnitOutline(
            lessons=[
                LessonSummary(
                    title=f"{unit.title} Lesson {i + 1}",
                    goal="x",
                    include_code_practice=False,
                    interactive_activity_types=[],
                )
                for i in range(count)
            ]
        )
        return StageOutcome(content=outline, passed=True, attempts=[])

    graph = build_graph(
        overview_fn=_passing_overview,
        unit_outline_fn=variable_unit_outline,
        lesson_content_fn=_passing_lesson_content,
    )
    course = run_generation(
        topic="testing",
        audience="beginners",
        num_units=3,
        lessons_per_unit=1,
        graph=graph,
    )

    assert [len(unit.lessons) for unit in course.units] == [1, 2, 3]


def test_graph_passes_language_to_every_stage_and_the_assembled_course():
    seen: list[tuple[str, str]] = []

    def overview_fn(**kwargs):
        seen.append(("overview", kwargs["language"]))
        return _passing_overview(**kwargs)

    def unit_outline_fn(**kwargs):
        seen.append(("unit", kwargs["language"]))
        outline = _passing_unit_outline(**kwargs).content
        for lesson in outline.lessons:
            lesson.include_code_practice = True
        return StageOutcome(content=outline, passed=True, attempts=[])

    def lesson_content_fn(**kwargs):
        seen.append(("lesson", kwargs["language"]))
        content = LessonContent(
            written_lesson_markdown="# Adding",
            code_practice=GeneratedFunctionPractice(
                title="Add",
                function_signature="add(a, b)",
                description="Add two numbers.",
                reference_solution="def add(a, b):\n    return a + b",
                test_suite=[
                    GeneratedTestCase(input=[1, 2], expected_output=3),
                    GeneratedTestCase(input=[5, 5], expected_output=10),
                ],
            ),
            interactive_activities=[],
        )
        return StageOutcome(content=content, passed=True, attempts=[])

    graph = build_graph(
        overview_fn=overview_fn,
        unit_outline_fn=unit_outline_fn,
        lesson_content_fn=lesson_content_fn,
    )
    course = run_generation(
        topic="testing",
        audience="beginners",
        num_units=2,
        lessons_per_unit=2,
        language="python",
        graph=graph,
    )

    assert {language for _, language in seen} == {"python"}
    assert [stage for stage, _ in seen].count("lesson") == 4
    practices = [
        practice
        for unit in course.units
        for lesson in unit.lessons
        for practice in lesson.codePractices
    ]
    assert len(practices) == 4
    assert {practice.language for practice in practices} == {"python"}
