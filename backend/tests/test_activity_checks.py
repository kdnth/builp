from app.agent.activity_checks import (
    check_activity_grounding,
    check_fill_blank_answerability,
    check_multiple_choice_quality,
)
from app.agent.checks import check_lesson_content
from app.agent.schemas import (
    GeneratedFillBlankActivity,
    GeneratedMatchingActivity,
    GeneratedMultipleChoiceActivity,
    LessonContent,
)


def _fill_blank(text: str, accepted: list[list[str]], description: str = "Fill in."):
    return GeneratedFillBlankActivity(
        description=description,
        text=text,
        blanks=[{"accepted": values} for values in accepted],
    )


# The real generated activity from a Python lambda lesson
REAL_FREE_CHOICE = _fill_blank(
    "subtract = {{blank}} a, b: a {{blank}} b\nresult = subtract(10, {{blank}})",
    [["lambda"], ["-"], ["3", "4", "5", "1", "2", "6", "7", "8", "9", "0"]],
)


def test_free_choice_blank_is_rejected():
    problems = check_fill_blank_answerability(REAL_FREE_CHOICE)
    assert len(problems) == 1
    assert "blank 3" in problems[0]
    assert "free to choose" in problems[0]


def test_spelling_and_case_variants_are_accepted():
    activity = _fill_blank(
        "Set the {{blank}} property.", [["color", "colour", "COLOR", "Color"]]
    )
    assert check_fill_blank_answerability(activity) == []


def test_different_answers_in_one_blank_are_rejected():
    activity = _fill_blank("Use the {{blank}} keyword.", [["lambda", "def"]])
    problems = check_fill_blank_answerability(activity)
    assert len(problems) == 1
    assert "not the same answer written differently" in problems[0]


def test_too_many_accepted_answers_are_rejected():
    activity = _fill_blank(
        "Name a {{blank}}.",
        [["alpha", "alphas", "alphabet", "alphabets", "alphabetic"]],
    )
    assert any(
        "at most 4" in problem for problem in check_fill_blank_answerability(activity)
    )


def test_too_many_blanks_are_rejected():
    activity = _fill_blank(
        "{{blank}} a {{blank}} b {{blank}} c {{blank}}",
        [["one"], ["two"], ["three"], ["four"]],
    )
    assert any(
        "at most 3" in problem for problem in check_fill_blank_answerability(activity)
    )


def test_blanks_with_nothing_between_them_are_rejected():
    activity = _fill_blank("Write {{blank}} {{blank}} here.", [["def"], ["name"]])
    problems = check_fill_blank_answerability(activity)
    assert any("no word between" in problem for problem in problems)


def test_multiple_choice_repeated_options_are_rejected():
    activity = GeneratedMultipleChoiceActivity(
        question="What does map return?",
        options=["A list", "a list", "A number"],
        correct_index=0,
    )
    assert any(
        "options that repeat" in problem
        for problem in check_multiple_choice_quality(activity)
    )


def test_multiple_choice_giveaway_length_is_rejected():
    activity = GeneratedMultipleChoiceActivity(
        question="What is a lambda?",
        options=[
            "Nope",
            "A small anonymous function written inline that returns its expression",
            "A loop",
        ],
        correct_index=1,
    )
    assert any(
        "much longer" in problem for problem in check_multiple_choice_quality(activity)
    )


def test_multiple_choice_answer_inside_the_question_is_rejected():
    activity = GeneratedMultipleChoiceActivity(
        question="Which keyword makes an anonymous function, the lambda keyword?",
        options=["the lambda keyword", "the def keyword"],
        correct_index=0,
    )
    assert any(
        "appears in the question" in problem
        for problem in check_multiple_choice_quality(activity)
    )


def test_good_multiple_choice_passes():
    activity = GeneratedMultipleChoiceActivity(
        question="What does a lambda expression return?",
        options=["Its expression", "Always None", "A list of values"],
        correct_index=0,
    )
    assert check_multiple_choice_quality(activity) == []


def test_grounding_rejects_answers_the_lesson_never_mentions():
    lesson = "# Lambdas\nA lambda expression has no name."
    ungrounded = _fill_blank("Use a {{blank}} instead.", [["decorator"]])
    grounded = _fill_blank("Use a {{blank}} instead.", [["lambda"]])

    assert check_activity_grounding(ungrounded, lesson)
    assert check_activity_grounding(grounded, lesson) == []


def test_grounding_ignores_symbols_and_short_answers():
    lesson = "# Operators\nSubtraction uses the minus operator."
    activity = _fill_blank("a {{blank}} b", [["-"]])
    assert check_activity_grounding(activity, lesson) == []


def test_grounding_checks_matching_terms():
    lesson = "# Lambdas\nA lambda expression has no name."
    activity = GeneratedMatchingActivity(
        pairs=[
            {"term": "lambda", "definition": "an expression with no name"},
            {"term": "decorator", "definition": "wraps a function"},
            {"term": "generator", "definition": "yields values"},
        ]
    )
    problems = check_activity_grounding(activity, lesson)
    assert len(problems) == 2


def test_check_lesson_content_reports_the_real_activity():
    content = LessonContent(
        written_lesson_markdown="# Lambdas\nWrite `lambda a, b: a - b`.",
        code_practice=None,
        interactive_activities=[REAL_FREE_CHOICE],
    )
    problems = check_lesson_content(content, language="python")
    assert any("free to choose" in problem for problem in problems)
