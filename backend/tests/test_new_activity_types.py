from app.agent.activity_checks import (
    check_activity_grounding,
    check_categorize_answerability,
    check_option_explanations,
    check_ordering_answerability,
)
from app.agent.assemble import assemble_lesson
from app.agent.checks import check_lesson_content, check_numeric_consistency
from app.agent.schemas import (
    GeneratedCategorizeActivity,
    GeneratedMultipleChoiceActivity,
    GeneratedNumericActivity,
    GeneratedOrderingActivity,
)
from tests.factories import make_lesson_content

STEPS = GeneratedOrderingActivity(
    basis="process steps",
    items=["Measure the flour", "Mix the dough", "Bake the loaf"],
    explanation="Each step needs the one before it.",
)

GROUPS = GeneratedCategorizeActivity(
    categories=["Fixed cost", "Variable cost"],
    items=[
        {"text": "Rent", "category": "Fixed cost"},
        {"text": "Flour", "category": "Variable cost"},
        {"text": "Insurance", "category": "Fixed cost"},
    ],
)


def test_ordering_rejects_repeated_items():
    activity = GeneratedOrderingActivity(
        basis="chronological", items=["1914", "1918", "1914"]
    )
    problems = check_ordering_answerability(activity)
    assert any("repeats an item" in problem for problem in problems)


def test_good_ordering_passes():
    assert check_ordering_answerability(STEPS) == []


def test_categorize_rejects_a_category_that_does_not_exist():
    activity = GeneratedCategorizeActivity(
        categories=["Fixed cost", "Variable cost"],
        items=[
            {"text": "Rent", "category": "Fixed cost"},
            {"text": "Flour", "category": "Sunk cost"},
            {"text": "Insurance", "category": "Fixed cost"},
        ],
    )
    problems = check_categorize_answerability(activity)
    assert any("not one of" in problem for problem in problems)


def test_categorize_rejects_an_unused_category():
    activity = GeneratedCategorizeActivity(
        categories=["Fixed cost", "Variable cost", "Sunk cost"],
        items=[
            {"text": "Rent", "category": "Fixed cost"},
            {"text": "Flour", "category": "Variable cost"},
            {"text": "Insurance", "category": "Fixed cost"},
        ],
    )
    problems = check_categorize_answerability(activity)
    assert any("only a distractor" in problem for problem in problems)


def test_good_categorize_passes():
    assert check_categorize_answerability(GROUPS) == []


def test_categorize_categories_must_come_from_the_lesson():
    lesson = "# Costs\nA fixed cost does not change with output."
    problems = check_activity_grounding(GROUPS, lesson)
    assert any("Variable cost" in problem for problem in problems)
    assert not any("Fixed cost" in problem for problem in problems)


def test_numeric_answer_is_verified_by_running_the_expression():
    correct = GeneratedNumericActivity(
        question="Prices went from 100 to 120. What is the percent change?",
        answer=20,
        answer_expression="(120 - 100) / 100 * 100",
        unit="percent",
    )
    wrong = GeneratedNumericActivity(
        question="Prices went from 100 to 120. What is the percent change?",
        answer=25,
        answer_expression="(120 - 100) / 100 * 100",
    )

    assert check_numeric_consistency(correct) is None
    problem = check_numeric_consistency(wrong)
    assert problem is not None and "computes 20.0" in problem


def test_numeric_tolerance_allows_a_rounded_answer():
    rounded = GeneratedNumericActivity(
        question="What is pi to two places?",
        answer=3.14,
        answer_expression="math.pi",
        tolerance=0.01,
    )
    assert check_numeric_consistency(rounded) is None


def test_numeric_expression_cannot_reach_the_system():
    sneaky = GeneratedNumericActivity(
        question="x", answer=1, answer_expression="__import__('os').getpid()"
    )
    problem = check_numeric_consistency(sneaky)
    assert problem is not None and "answer_expression failed" in problem


def test_option_explanations_must_cover_every_option():
    activity = GeneratedMultipleChoiceActivity(
        question="Which cost is fixed?",
        options=["Rent", "Flour", "Packaging"],
        option_explanations=["Rent does not change with output.", "Flour does."],
        correct_index=0,
    )
    problems = check_option_explanations(activity)
    assert any("one for each" in problem for problem in problems)


def test_lesson_check_runs_the_new_activity_checks():
    content = make_lesson_content(
        markdown="# Costs\nA fixed cost and a variable cost differ.",
        activities=[
            GeneratedOrderingActivity(basis="", items=["a", "b", "c"]),
            GeneratedNumericActivity(question="q", answer=5, answer_expression="2 + 2"),
        ],
    )

    problems = check_lesson_content(content, language="none")

    assert any("no basis" in problem for problem in problems)
    assert any("answer_expression computes 4.0" in problem for problem in problems)


def test_new_activities_are_assembled_into_the_course_shape():
    content = make_lesson_content(
        markdown="# Costs",
        activities=[
            STEPS,
            GROUPS,
            GeneratedNumericActivity(
                question="q",
                answer=20,
                answer_expression="20",
                tolerance=0.5,
                unit="percent",
                explanation="Because.",
            ),
            GeneratedMultipleChoiceActivity(
                question="Which is fixed?",
                options=["Rent", "Flour"],
                option_explanations=["It does not change.", "It changes."],
                passage="| cost | amount |\n| --- | --- |\n| Rent | 100 |",
                correct_index=0,
                explanation="Rent is fixed.",
            ),
        ],
    )

    lesson = assemble_lesson("Costs", content, "javascript")
    activities = lesson.pages[1].practice.activities

    assert [activity.type for activity in activities] == [
        "ordering",
        "categorize",
        "numeric",
        "multipleChoice",
    ]
    assert activities[0].items[0] == "Measure the flour"
    assert activities[0].explanation == "Each step needs the one before it."
    assert {item.category for item in activities[1].items} == {
        "Fixed cost",
        "Variable cost",
    }
    assert all(item.id for item in activities[1].items)
    assert (activities[2].tolerance, activities[2].unit) == (0.5, "percent")
    assert activities[3].optionExplanations == [
        "It does not change.",
        "It changes.",
    ]
    assert activities[3].passage.startswith("| cost |")


def test_a_lesson_can_hold_eight_activities():
    activities = [
        GeneratedMultipleChoiceActivity(
            question=f"Question {index}?",
            options=["Yes", "No"],
            correct_index=0,
        )
        for index in range(8)
    ]
    content = make_lesson_content(markdown="# Many", activities=activities)
    assert len(content.interactive_activities) == 8
