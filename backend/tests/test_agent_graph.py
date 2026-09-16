from app.agent.graph import build_graph, run_generation
from app.agent.schemas import (
    GeneratedFunctionPractice,
    GeneratedMultipleChoiceActivity,
    GeneratedTestCase,
    UnitOutline,
    UnitSummary,
)
from app.agent.stage import StageOutcome
from tests.factories import (
    make_brief,
    make_lesson_content,
    make_lesson_summary,
    make_overview,
)


def _passing_overview(*, topic, audience, num_units, **kwargs):
    overview = make_overview(
        title=f"Learn {topic}",
        audience=audience,
        units=[
            UnitSummary(title=f"Unit {i + 1}", goal=f"Cover part {i + 1}.")
            for i in range(num_units)
        ],
    )
    return StageOutcome(content=overview, passed=True, attempts=[])


def _passing_unit_outline(*, overview, unit, lessons_per_unit, **kwargs):
    outline = UnitOutline(
        lessons=[
            make_lesson_summary(
                title=f"{unit.title} Lesson {i + 1}",
                activity_types=["multipleChoice"],
            )
            for i in range(lessons_per_unit)
        ]
    )
    return StageOutcome(content=outline, passed=True, attempts=[])


def _passing_lesson_content(*, overview, unit, outline, lesson_index, **kwargs):
    content = make_lesson_content(
        markdown=f"# {outline.lessons[lesson_index].title}",
        code_practice=None,
        activities=[
            GeneratedMultipleChoiceActivity(
                question="Is this a test?", options=["Yes", "No"], correct_index=0
            )
        ],
    )
    return StageOutcome(content=content, passed=True, attempts=[])


def _graph(**overrides):
    functions = {
        "overview_fn": _passing_overview,
        "unit_outline_fn": _passing_unit_outline,
        "lesson_content_fn": _passing_lesson_content,
    }
    functions.update(overrides)
    return build_graph(**functions)


def test_graph_produces_a_fully_assembled_course():
    course = run_generation(
        topic="testing",
        audience="beginners",
        num_units=3,
        lessons_per_unit=2,
        graph=_graph(),
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

    course = run_generation(
        topic="testing",
        audience="beginners",
        num_units=2,
        lessons_per_unit=1,
        graph=_graph(),
    )
    Course.model_validate(course.model_dump())


def test_graph_handles_uneven_lesson_counts_per_unit():
    def variable_unit_outline(*, overview, unit, lessons_per_unit, **kwargs):
        # unit N gets N lessons, not a fixed count
        count = int(unit.title.split()[-1])
        outline = UnitOutline(
            lessons=[
                make_lesson_summary(title=f"{unit.title} Lesson {i + 1}")
                for i in range(count)
            ]
        )
        return StageOutcome(content=outline, passed=True, attempts=[])

    course = run_generation(
        topic="testing",
        audience="beginners",
        num_units=3,
        lessons_per_unit=1,
        graph=_graph(unit_outline_fn=variable_unit_outline),
    )

    assert [len(unit.lessons) for unit in course.units] == [1, 2, 3]


def test_every_lesson_sees_the_whole_course_map():
    maps: list[str] = []

    def recording_lesson(*, course_map, **kwargs):
        maps.append(course_map)
        return _passing_lesson_content(course_map=course_map, **kwargs)

    run_generation(
        topic="testing",
        audience="beginners",
        num_units=2,
        lessons_per_unit=2,
        graph=_graph(lesson_content_fn=recording_lesson),
    )

    assert len(maps) == 4
    for course_map in maps:
        # the other unit's lessons are in the map, not only this lesson's
        assert "Unit 1: Unit 1" in course_map
        assert "Unit 2: Unit 2" in course_map
        assert course_map.count("Lesson") >= 4
        assert course_map.count("you are writing this lesson") == 1
    assert len(set(maps)) == 4


def test_lesson_generation_can_be_routed_by_profile():
    routed: list[str] = []

    def narrative_outline(*, overview, unit, lessons_per_unit, **kwargs):
        return StageOutcome(
            content=UnitOutline(
                lessons=[make_lesson_summary(profile="narrative", title="Story")]
            ),
            passed=True,
            attempts=[],
        )

    def narrative_lesson(**kwargs):
        routed.append("narrative")
        return _passing_lesson_content(**kwargs)

    def shared_lesson(**kwargs):
        routed.append("shared")
        return _passing_lesson_content(**kwargs)

    run_generation(
        topic="history",
        audience="beginners",
        num_units=1,
        lessons_per_unit=1,
        graph=build_graph(
            overview_fn=_passing_overview,
            unit_outline_fn=narrative_outline,
            lesson_content_fn=shared_lesson,
            lesson_content_fns={"narrative": narrative_lesson},
        ),
    )

    assert routed == ["narrative"]


def test_code_practice_language_comes_from_the_brief():
    def python_overview(**kwargs):
        overview = _passing_overview(**kwargs).content
        overview.brief = make_brief(code_practice_policy="python")
        return StageOutcome(content=overview, passed=True, attempts=[])

    def outline_with_code(*, overview, unit, lessons_per_unit, **kwargs):
        return StageOutcome(
            content=UnitOutline(
                lessons=[make_lesson_summary(include_code_practice=True)]
            ),
            passed=True,
            attempts=[],
        )

    def lesson_with_code(**kwargs):
        content = make_lesson_content(
            markdown="# Adding",
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
            activities=[],
        )
        return StageOutcome(content=content, passed=True, attempts=[])

    course = run_generation(
        topic="stats",
        audience="beginners",
        num_units=1,
        lessons_per_unit=1,
        course_type="general",
        language="auto",
        graph=build_graph(
            overview_fn=python_overview,
            unit_outline_fn=outline_with_code,
            lesson_content_fn=lesson_with_code,
        ),
    )

    pages = course.units[0].lessons[0].pages
    code = next(page for page in pages if page.kind == "code")
    assert code.practice.language == "python"
