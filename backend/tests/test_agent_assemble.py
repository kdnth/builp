from app.agent.assemble import assemble_course, assemble_lesson
from app.agent.schemas import (
    CourseOverview,
    GeneratedFillBlankActivity,
    GeneratedFunctionPractice,
    GeneratedMultipleChoiceActivity,
    GeneratedTestCase,
    LessonContent,
    UnitSummary,
)


def test_assemble_lesson_with_code_and_activities():
    content = LessonContent(
        written_lesson_markdown="# Adding numbers\nUse `+`.",
        code_practice=GeneratedFunctionPractice(
            title="Add",
            function_signature="add(a, b)",
            description="Add two numbers.",
            reference_solution="function add(a, b) { return a + b }",
            test_suite=[
                GeneratedTestCase(input=[1, 2], expected_output=3),
                GeneratedTestCase(input=[5, 5], expected_output=10),
            ],
        ),
        interactive_activities=[
            GeneratedMultipleChoiceActivity(
                question="What does + do?",
                options=["Adds", "Subtracts"],
                correct_index=0,
            ),
            GeneratedFillBlankActivity(
                text="{{blank}} adds two numbers.",
                blanks=[{"accepted": ["+"]}],
            ),
        ],
    )

    lesson = assemble_lesson("Addition", content)

    assert lesson.title == "Addition"
    assert lesson.writtenLesson.markdown.startswith("# Adding numbers")
    assert len(lesson.codePractices) == 1
    assert lesson.codePractices[0].testSuite[0].expectedOutput == 3
    assert len(lesson.interactivePractices) == 1
    assert len(lesson.interactivePractices[0].activities) == 2

    fill_blank = lesson.interactivePractices[0].activities[1]
    assert fill_blank.blanks[0].position == 0

    # every generated id is unique
    ids = [
        lesson.id,
        lesson.writtenLesson.id,
        lesson.codePractices[0].id,
        lesson.interactivePractices[0].id,
        *[a.id for a in lesson.interactivePractices[0].activities],
    ]
    assert len(ids) == len(set(ids))


def test_assemble_lesson_with_no_code_or_activities():
    content = LessonContent(
        written_lesson_markdown="# Just reading",
        code_practice=None,
        interactive_activities=[],
    )
    lesson = assemble_lesson("Reading", content)
    assert lesson.codePractices == []
    assert lesson.interactivePractices == []


def test_assemble_course_matches_real_schema():
    overview = CourseOverview(
        title="Intro to JS",
        description="Learn the basics.",
        audience="Complete beginners.",
        units=[
            UnitSummary(title="Unit One", goal="Cover the basics."),
            UnitSummary(title="Unit Two", goal="Build on unit one."),
        ],
    )

    lesson = assemble_lesson(
        "Lesson",
        LessonContent(
            written_lesson_markdown="# hi",
            code_practice=None,
            interactive_activities=[],
        ),
    )

    course = assemble_course(overview, unit_lessons=[[lesson], [lesson]])

    assert course.title == "Intro to JS"
    assert len(course.units) == 2
    assert course.units[0].title == "Unit One"

    # round-trips through the real, independently-validated Course schema
    from app.schemas.course import Course

    Course.model_validate(course.model_dump())
