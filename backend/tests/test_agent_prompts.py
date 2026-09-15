from app.agent.prompts import (
    lesson_content_evaluate_prompt,
    lesson_content_generate_prompt,
    overview_generate_prompt,
    unit_outline_generate_prompt,
)
from app.agent.schemas import (
    CourseOverview,
    LessonContent,
    LessonSummary,
    UnitOutline,
    UnitSummary,
)

_OVERVIEW = CourseOverview(
    title="Course",
    description="A course.",
    audience="Beginners.",
    units=[UnitSummary(title="Unit 1", goal="Basics.")],
)
_UNIT = _OVERVIEW.units[0]
_OUTLINE = UnitOutline(
    lessons=[
        LessonSummary(
            title="Lesson 1",
            goal="Add numbers.",
            include_code_practice=True,
            interactive_activity_types=[],
        )
    ]
)


def _text(messages) -> str:
    parts = []
    for message in messages:
        content = message.content
        if isinstance(content, list):
            parts.extend(block["text"] for block in content)
        else:
            parts.append(content)
    return "\n".join(parts)


def test_overview_and_unit_prompts_name_the_language():
    overview = overview_generate_prompt(
        topic="Loops",
        audience="Beginners",
        num_units=1,
        language="python",
        feedback=None,
    )
    unit = unit_outline_generate_prompt(
        overview=_OVERVIEW,
        unit=_UNIT,
        lessons_per_unit=1,
        language="python",
        feedback=None,
        provider="anthropic",
    )
    assert "Programming language: Python" in _text(overview)
    assert "Programming language: Python" in _text(unit)


def test_python_lesson_prompt_asks_for_python_code():
    text = _text(
        lesson_content_generate_prompt(
            overview=_OVERVIEW,
            unit=_UNIT,
            outline=_OUTLINE,
            lesson_index=0,
            language="python",
            feedback=None,
            provider="anthropic",
        )
    )
    assert "Write every code example in Python." in text
    assert "correct Python function" in text
    assert "def add(a, b)" in text
    assert "JavaScript" not in text
    assert "{{blank}}" in text


def test_javascript_lesson_prompt_asks_for_javascript_code():
    text = _text(
        lesson_content_generate_prompt(
            overview=_OVERVIEW,
            unit=_UNIT,
            outline=_OUTLINE,
            lesson_index=0,
            language="javascript",
            feedback=None,
            provider="anthropic",
        )
    )
    assert "Write every code example in JavaScript." in text
    assert "function add(a, b) { return a + b }" in text
    assert "Python function" not in text


def test_lesson_review_prompt_names_the_language():
    text = _text(
        lesson_content_evaluate_prompt(
            overview=_OVERVIEW,
            unit=_UNIT,
            outline=_OUTLINE,
            lesson_index=0,
            language="python",
            content=LessonContent(
                written_lesson_markdown="# hi", interactive_activities=[]
            ),
            provider="anthropic",
        )
    )
    assert "Course programming language: Python" in text
