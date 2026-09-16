from app.agent.assemble import assemble_course, assemble_lesson
from app.agent.schemas import (
    GeneratedFillBlankActivity,
    GeneratedFunctionPractice,
    GeneratedMultipleChoiceActivity,
    GeneratedTestCase,
    UnitSummary,
)
from tests.factories import make_lesson_content, make_overview


def test_assemble_lesson_with_code_and_activities():
    content = make_lesson_content(
        markdown="# Adding numbers\nUse `+`.",
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
        activities=[
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

    lesson = assemble_lesson("Addition", content, "javascript")

    assert lesson.title == "Addition"
    # read, then the code practice, then the check
    assert [page.kind for page in lesson.pages] == ["written", "code", "interactive"]

    written, code, interactive = lesson.pages
    assert written.written.markdown.startswith("# Adding numbers")
    assert code.practice.language == "javascript"
    assert code.practice.testSuite[0].expectedOutput == 3
    assert len(interactive.practice.activities) == 2

    fill_blank = interactive.practice.activities[1]
    assert fill_blank.blanks[0].position == 0

    # every generated id is unique
    ids = [
        lesson.id,
        written.written.id,
        code.practice.id,
        interactive.practice.id,
        *[activity.id for activity in interactive.practice.activities],
    ]
    assert len(ids) == len(set(ids))


def test_assemble_lesson_with_no_code_or_activities():
    content = make_lesson_content(
        markdown="# Just reading",
        code_practice=None,
        activities=[],
    )
    lesson = assemble_lesson("Reading", content, "javascript")
    assert [page.kind for page in lesson.pages] == ["written"]


def test_assemble_lesson_sets_python_language_on_code_practice():
    content = make_lesson_content(
        markdown="# Adding numbers",
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

    lesson = assemble_lesson("Addition", content, "python")

    code = next(page for page in lesson.pages if page.kind == "code")
    assert code.practice.language == "python"


def test_assemble_course_matches_real_schema():
    overview = make_overview(
        title="Intro to JS",
        units=[
            UnitSummary(title="Unit One", goal="Cover the basics."),
            UnitSummary(title="Unit Two", goal="Build on unit one."),
        ],
    )

    lesson = assemble_lesson(
        "Lesson",
        make_lesson_content(
            markdown="# hi",
            code_practice=None,
            activities=[],
        ),
        "javascript",
    )

    course = assemble_course(overview, unit_lessons=[[lesson], [lesson]])

    assert course.title == "Intro to JS"
    assert len(course.units) == 2
    assert course.units[0].title == "Unit One"

    # round-trips through the real, independently-validated Course schema
    from app.schemas.course import Course

    Course.model_validate(course.model_dump())


def test_interleaved_sections_become_read_then_check_pages():
    content = make_lesson_content(
        sections=[
            {
                "title": "What it is",
                "markdown": "text",
                "activities": [
                    {
                        "type": "multipleChoice",
                        "question": "q",
                        "options": ["a", "b"],
                        "correct_index": 0,
                    }
                ],
            },
            {"title": "How to use it", "markdown": "more"},
        ]
    )

    lesson = assemble_lesson("Lambdas", content, "python")

    assert [page.kind for page in lesson.pages] == [
        "written",
        "interactive",
        "written",
    ]
    assert lesson.pages[0].written.title == "What it is"
    assert lesson.pages[1].practice.title == "What it is check"
    assert lesson.pages[2].written.title == "How to use it"


def test_lesson_pages_reads_old_and_new_lessons_the_same_way():
    from app.schemas.course import lesson_pages

    new_lesson = assemble_lesson(
        "Reading", make_lesson_content(markdown="# Text"), "javascript"
    )
    old_lesson = new_lesson.model_copy(
        update={
            "pages": None,
            "writtenLesson": new_lesson.pages[0].written,
            "codePractices": [],
            "interactivePractices": [],
        }
    )

    assert [page.kind for page in lesson_pages(old_lesson)] == ["written"]
    assert lesson_pages(old_lesson)[0].written.markdown == "# Text"
    assert lesson_pages(new_lesson) == new_lesson.pages
