from unittest.mock import patch

from app.agent.llm import CallUsage, GenerationModelConfig
from app.agent.schemas import (
    ActivitySolutions,
    EvaluationResult,
    GeneratedFillBlankActivity,
    GeneratedMultipleChoiceActivity,
    LessonContent,
    SolvedActivity,
)
from app.agent.solver import render_activities, solve_activities

MODEL_CONFIG = GenerationModelConfig(provider="anthropic")

FILL_BLANK = GeneratedFillBlankActivity(
    description="Complete the expression.",
    text="subtract = {{blank}} a, b: a {{blank}} b",
    blanks=[{"accepted": ["lambda"]}, {"accepted": ["-"]}],
)

MULTIPLE_CHOICE = GeneratedMultipleChoiceActivity(
    question="What does a lambda return?",
    options=["Its expression", "Always None"],
    correct_index=0,
)


class FakeModel:
    def __init__(self, result):
        self._result = result
        self.calls = 0
        self.messages = None

    def with_structured_output(self, schema, include_raw=False):
        return self

    def invoke(self, messages):
        self.calls += 1
        self.messages = messages
        return {"parsed": self._result, "raw": None, "parsing_error": None}


def _run(solutions, activities):
    content = LessonContent(
        written_lesson_markdown="# Lambdas\nA lambda returns its expression.",
        code_practice=None,
        interactive_activities=activities,
    )
    model = FakeModel(ActivitySolutions(activities=solutions))
    calls: list[CallUsage] = []
    with patch("app.agent.llm.get_model", return_value=model):
        problems = solve_activities(
            content=content, model_config=MODEL_CONFIG, calls=calls
        )
    return problems, model, calls


def test_solver_prompt_hides_the_answer_key():
    blanks_text = render_activities([(1, FILL_BLANK)])
    choice_text = render_activities([(2, MULTIPLE_CHOICE)])

    assert "___(1)___" in blanks_text and "___(2)___" in blanks_text
    assert "{{blank}}" not in blanks_text
    # "lambda" and "-" are the accepted answers
    assert "lambda" not in blanks_text
    assert "a - b" not in blanks_text

    assert "Its expression" in choice_text and "Always None" in choice_text
    assert "correct" not in choice_text.lower()


def test_agreement_without_another_answer_is_clean():
    problems, model, calls = _run(
        [
            SolvedActivity(activity_number=1, answer="lambda | -"),
            SolvedActivity(activity_number=2, answer="Its expression"),
        ],
        [FILL_BLANK, MULTIPLE_CHOICE],
    )

    assert problems == []
    assert model.calls == 1
    assert [call.purpose for call in calls] == ["solve"]


def test_blank_answer_that_differs_from_the_key_is_reported():
    problems, _, _ = _run(
        [SolvedActivity(activity_number=1, answer="def | +")], [FILL_BLANK]
    )

    assert len(problems) == 2
    assert "blank 1" in problems[0] and '"def"' in problems[0]


def test_second_defensible_blank_answer_is_reported():
    problems, _, _ = _run(
        [
            SolvedActivity(
                activity_number=1,
                answer="lambda | -",
                other_defensible_answer="lambda | +",
            )
        ],
        [FILL_BLANK],
    )

    assert len(problems) == 1
    assert "blank 2" in problems[0]
    assert "more than one correct answer" in problems[0]


def test_case_and_spacing_differences_are_not_reported():
    problems, _, _ = _run(
        [SolvedActivity(activity_number=1, answer=" Lambda |  - ")], [FILL_BLANK]
    )
    assert problems == []


def test_multiple_choice_disagreement_is_reported():
    problems, _, _ = _run(
        [SolvedActivity(activity_number=1, answer="Always None")], [MULTIPLE_CHOICE]
    )

    assert len(problems) == 1
    assert "a reader chose" in problems[0]


def test_second_defensible_option_is_reported():
    problems, _, _ = _run(
        [
            SolvedActivity(
                activity_number=1,
                answer="Its expression",
                other_defensible_answer="Always None",
            )
        ],
        [MULTIPLE_CHOICE],
    )

    assert len(problems) == 1
    assert "more than one correct option" in problems[0]


def test_an_alternative_that_repeats_the_key_is_ignored():
    problems, _, _ = _run(
        [
            SolvedActivity(
                activity_number=1,
                answer="Its expression",
                other_defensible_answer="its expression",
            )
        ],
        [MULTIPLE_CHOICE],
    )
    assert problems == []


def test_a_lesson_without_solvable_activities_makes_no_call():
    content = LessonContent(
        written_lesson_markdown="# Lambdas",
        code_practice=None,
        interactive_activities=[],
    )
    model = FakeModel(ActivitySolutions(activities=[]))
    calls: list[CallUsage] = []
    with patch("app.agent.llm.get_model", return_value=model):
        problems = solve_activities(
            content=content, model_config=MODEL_CONFIG, calls=calls
        )

    assert problems == []
    assert model.calls == 0
    assert calls == []


def test_lesson_evaluation_skips_the_judge_when_the_solver_objects():
    from app.agent import nodes
    from app.agent.schemas import (
        CourseOverview,
        LessonSummary,
        UnitOutline,
        UnitSummary,
    )

    overview = CourseOverview(
        title="C",
        description="d",
        audience="a",
        units=[UnitSummary(title="U", goal="g")],
    )
    outline = UnitOutline(
        lessons=[
            LessonSummary(
                title="L",
                goal="g",
                include_code_practice=False,
                interactive_activity_types=["multipleChoice"],
            )
        ]
    )
    content = LessonContent(
        written_lesson_markdown="# L", code_practice=None, interactive_activities=[]
    )
    judge_calls = []

    def fake_invoke(*, schema, messages, tier, model_config, purpose, calls):
        if schema is LessonContent:
            return content
        judge_calls.append(schema)
        return EvaluationResult(passed=True, score=5, feedback="fine")

    with (
        patch.object(nodes, "invoke_structured", fake_invoke),
        patch.object(nodes, "solve_activities", return_value=["activity 1 is unclear"]),
    ):
        outcome = nodes.generate_lesson_content(
            overview=overview,
            unit=overview.units[0],
            outline=outline,
            lesson_index=0,
            language="python",
            model_config=MODEL_CONFIG,
        )

    assert outcome.passed is False
    assert judge_calls == []
    assert "activity 1 is unclear" in outcome.attempts[-1].evaluation.feedback
