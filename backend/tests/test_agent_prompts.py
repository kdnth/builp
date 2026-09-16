from app.agent.prompts import (
    lesson_content_evaluate_prompt,
    lesson_content_generate_prompt,
    overview_generate_prompt,
    render_course_map,
    unit_outline_generate_prompt,
)
from tests.factories import make_brief, make_lesson_content, make_outline, make_overview

_OVERVIEW = make_overview()
_UNIT = _OVERVIEW.units[0]
_OUTLINE = make_outline(include_code_practice=True)


def _text(messages) -> str:
    parts = []
    for message in messages:
        content = message.content
        if isinstance(content, list):
            parts.extend(block["text"] for block in content)
        else:
            parts.append(content)
    return "\n".join(parts)


def _overview_text(**overrides) -> str:
    values = {
        "topic": "Loops",
        "audience": "Beginners",
        "num_units": 1,
        "course_type": "programming",
        "language": "python",
        "level": "beginner",
        "learning_goals": None,
        "notes": None,
        "feedback": None,
    }
    values.update(overrides)
    return _text(overview_generate_prompt(**values))


def test_overview_prompt_carries_the_user_context():
    text = _overview_text(
        level="advanced",
        learning_goals="tune a query planner",
        notes="use UK spelling",
    )

    assert "Level: advanced" in text
    assert "tune a query planner" in text
    assert "use UK spelling" in text
    assert "Course type: programming" in text


def test_overview_prompt_fixes_the_language_when_the_user_chose_one():
    text = _overview_text(language="python")
    assert "set code_practice_policy to 'python'" in text


def test_overview_prompt_lets_the_model_choose_for_a_general_course():
    text = _overview_text(course_type="general", language="auto")

    assert "Course type: general subject" in text
    assert "you decide" in text


def test_overview_prompt_can_forbid_code_practice():
    text = _overview_text(course_type="general", language="none")
    assert "set code_practice_policy to 'none'" in text


def test_unit_outline_prompt_names_the_allowed_profiles():
    text = _text(
        unit_outline_generate_prompt(
            overview=_OVERVIEW,
            unit=_UNIT,
            lessons_per_unit=2,
            feedback=None,
            provider="anthropic",
        )
    )

    assert "programming, conceptual" in text
    assert "Code practices use JavaScript" in text
    assert "Glossary" in text


def test_unit_outline_prompt_forbids_code_when_the_course_has_none():
    overview = make_overview(
        brief=make_brief(code_practice_policy="none", lesson_profiles=["narrative"])
    )
    text = _text(
        unit_outline_generate_prompt(
            overview=overview,
            unit=overview.units[0],
            lessons_per_unit=2,
            feedback=None,
            provider="anthropic",
        )
    )

    assert "include_code_practice is always false" in text


def test_lesson_prompt_carries_the_brief_the_map_and_the_profile():
    course_map = render_course_map(_OVERVIEW, [(_UNIT, _OUTLINE)], current=(1, 1))
    text = _text(
        lesson_content_generate_prompt(
            overview=_OVERVIEW,
            unit=_UNIT,
            outline=_OUTLINE,
            lesson_index=0,
            course_map=course_map,
            reading_style="single",
            feedback=None,
            provider="anthropic",
        )
    )

    assert "Course map:" in text
    assert "you are writing this lesson" in text
    assert "This is a programming lesson" in text
    assert "correct JavaScript function" in text
    assert "a check that code works" in text


def test_lesson_prompt_without_code_practice_has_no_code_rules():
    overview = make_overview(
        brief=make_brief(lesson_profiles=["narrative"], code_practice_policy="none")
    )
    outline = make_outline(profile="narrative", include_code_practice=False)
    text = _text(
        lesson_content_generate_prompt(
            overview=overview,
            unit=overview.units[0],
            outline=outline,
            lesson_index=0,
            course_map="Course map:",
            reading_style="interleaved",
            feedback=None,
            provider="anthropic",
        )
    )

    assert "This lesson has no code practice" in text
    assert "This is a narrative lesson" in text
    assert "reference_solution" not in text


def test_lesson_review_prompt_uses_the_profile_criteria():
    overview = make_overview(
        brief=make_brief(lesson_profiles=["quantitative"], code_practice_policy="none")
    )
    outline = make_outline(profile="quantitative")
    text = _text(
        lesson_content_evaluate_prompt(
            overview=overview,
            unit=overview.units[0],
            outline=outline,
            lesson_index=0,
            content=make_lesson_content(
                markdown="# hi",
                activities=[],
            ),
            provider="anthropic",
        )
    )

    assert "units are consistent" in text
    assert "This course has no code practice." in text


def test_course_map_lists_every_unit_and_lesson():
    overview = make_overview(num_units=2)
    outlines = [
        (overview.units[0], make_outline(num_lessons=2)),
        (overview.units[1], make_outline(num_lessons=1)),
    ]

    text = render_course_map(overview, outlines, current=(2, 1))

    assert "Unit 1: Unit 1" in text and "Unit 2: Unit 2" in text
    assert "1.1 Lesson 1" in text and "1.2 Lesson 2" in text
    assert text.count("you are writing this lesson") == 1
    assert "2.1 Lesson 1 - Learn a thing.  <- you are writing this lesson" in text
