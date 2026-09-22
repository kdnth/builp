from unittest.mock import patch

from app.agent.llm import CallUsage, GenerationModelConfig
from app.agent.schemas import (
    ActivitySolutions,
    EvaluationResult,
    GeneratedFillBlankActivity,
    GeneratedFunctionPractice,
    GeneratedLessonActivityFix,
    GeneratedMultipleChoiceActivity,
    GeneratedSectionActivities,
    GeneratedTestCase,
    LessonContent,
    SolvedActivity,
)
from app.agent.solver import render_activities, solve_activities
from tests.factories import make_lesson_content

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
    content = make_lesson_content(
        markdown="# Lambdas\nA lambda returns its expression.",
        activities=activities,
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
    content = make_lesson_content(markdown="# Lambdas")
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
    from tests.factories import make_lesson_content, make_outline, make_overview

    overview = make_overview()
    outline = make_outline(activity_types=["multipleChoice"])
    content = make_lesson_content(
        markdown="# L",
        code_practice=None,
        activities=[],
    )
    judge_calls = []

    def fake_invoke(
        *, schema, messages, tier, model_config, purpose, calls, budget=None
    ):
        if schema is LessonContent:
            return content
        if schema is GeneratedLessonActivityFix:
            # A narrow retry: keep every section's activities empty
            # again, which is a valid (if unhelpful) fix - the solver is
            # patched to always object, so this loop never converges.
            return GeneratedLessonActivityFix(
                sections=[
                    GeneratedSectionActivities(section_index=index)
                    for index in range(len(content.sections))
                ]
            )
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
            course_map="Course map:",
            reading_style="single",
            model_config=MODEL_CONFIG,
        )

    assert outcome.passed is False
    assert judge_calls == []
    assert "activity 1 is unclear" in outcome.attempts[-1].evaluation.feedback


def test_generate_lesson_content_takes_the_narrow_path_after_activity_check_failure():
    from app.agent import nodes
    from tests.factories import make_lesson_content, make_outline, make_overview

    overview = make_overview()
    outline = make_outline(activity_types=["multipleChoice"])
    broken = make_lesson_content(
        markdown="# L",
        code_practice=None,
        activities=[
            GeneratedMultipleChoiceActivity(
                question="2 + 2?", options=["3", "4"], correct_index=5
            )
        ],
    )
    fixed_activity = GeneratedMultipleChoiceActivity(
        question="2 + 2?", options=["3", "4"], correct_index=1
    )
    schemas_seen = []

    def fake_invoke(
        *, schema, messages, tier, model_config, purpose, calls, budget=None
    ):
        schemas_seen.append(schema)
        if schema is LessonContent:
            return broken
        if schema is GeneratedLessonActivityFix:
            return GeneratedLessonActivityFix(
                sections=[
                    GeneratedSectionActivities(
                        section_index=0, activities=[fixed_activity]
                    )
                ]
            )
        return EvaluationResult(passed=True, score=5, feedback="fine")

    with (
        patch.object(nodes, "invoke_structured", fake_invoke),
        patch.object(nodes, "solve_activities", return_value=[]),
    ):
        outcome = nodes.generate_lesson_content(
            overview=overview,
            unit=overview.units[0],
            outline=outline,
            lesson_index=0,
            course_map="Course map:",
            reading_style="single",
            model_config=MODEL_CONFIG,
        )

    assert outcome.passed is True
    assert schemas_seen == [LessonContent, GeneratedLessonActivityFix, EvaluationResult]
    assert outcome.content.sections[0].activities == [fixed_activity]
    assert outcome.content.sections[0].markdown == broken.sections[0].markdown


def test_generate_lesson_content_takes_the_full_path_after_a_structural_check_failure():
    from app.agent import nodes
    from tests.factories import make_lesson_content, make_outline, make_overview

    overview = make_overview()
    outline = make_outline(include_code_practice=True)
    broken_practice = GeneratedFunctionPractice(
        title="Add",
        function_signature="add(a, b)",
        description="Add two numbers.",
        reference_solution="function add(a, b) { return a + b }",
        test_suite=[
            GeneratedTestCase(input=[1, 2], expected_output=999),
            GeneratedTestCase(input=[5, 5], expected_output=10),
        ],
    )
    broken = make_lesson_content(
        markdown="# L", code_practice=broken_practice, activities=[]
    )
    fixed = make_lesson_content(markdown="# L", code_practice=None, activities=[])
    schemas_seen = []

    def fake_invoke(
        *, schema, messages, tier, model_config, purpose, calls, budget=None
    ):
        schemas_seen.append(schema)
        if schema is LessonContent:
            return broken if schemas_seen.count(LessonContent) == 1 else fixed
        return EvaluationResult(passed=True, score=5, feedback="fine")

    with (
        patch.object(nodes, "invoke_structured", fake_invoke),
        patch.object(nodes, "solve_activities", return_value=[]),
    ):
        outcome = nodes.generate_lesson_content(
            overview=overview,
            unit=overview.units[0],
            outline=outline,
            lesson_index=0,
            course_map="Course map:",
            reading_style="single",
            model_config=MODEL_CONFIG,
        )

    assert outcome.passed is True
    assert schemas_seen == [LessonContent, LessonContent, EvaluationResult]


def test_generate_lesson_content_takes_the_full_path_after_a_judge_quality_failure():
    from app.agent import nodes
    from tests.factories import make_lesson_content, make_outline, make_overview

    overview = make_overview()
    outline = make_outline()
    content = make_lesson_content(markdown="# L", code_practice=None, activities=[])
    schemas_seen = []
    judge_calls = 0

    def fake_invoke(
        *, schema, messages, tier, model_config, purpose, calls, budget=None
    ):
        nonlocal judge_calls
        schemas_seen.append(schema)
        if schema is LessonContent:
            return content
        judge_calls += 1
        if judge_calls == 1:
            return EvaluationResult(passed=False, score=2, feedback="too shallow")
        return EvaluationResult(passed=True, score=5, feedback="fine")

    with (
        patch.object(nodes, "invoke_structured", fake_invoke),
        patch.object(nodes, "solve_activities", return_value=[]),
    ):
        outcome = nodes.generate_lesson_content(
            overview=overview,
            unit=overview.units[0],
            outline=outline,
            lesson_index=0,
            course_map="Course map:",
            reading_style="single",
            model_config=MODEL_CONFIG,
        )

    assert outcome.passed is True
    assert schemas_seen == [
        LessonContent,
        EvaluationResult,
        LessonContent,
        EvaluationResult,
    ]


def test_a_short_activity_fix_keeps_the_unmatched_sections_unchanged():
    """The model does not reliably return exactly one activities list per
    section, despite being asked to (a real, frequent failure mode found
    in the 2026-09-22 golden-set analysis). A short fix response should
    degrade gracefully - matched sections get their fix, and any section
    not covered by the fix keeps its original (already-fine) activities -
    rather than wasting the call and forcing the next attempt to a
    stronger, more expensive tier for nothing."""
    from app.agent import nodes
    from tests.factories import make_lesson_content, make_outline, make_overview

    overview = make_overview()
    outline = make_outline(activity_types=["multipleChoice"])
    broken = make_lesson_content(
        markdown="# L",
        code_practice=None,
        sections=[
            {
                "title": "Section 1",
                "markdown": "First half.",
                "activities": [
                    GeneratedMultipleChoiceActivity(
                        question="2 + 2?", options=["3", "4"], correct_index=5
                    )
                ],
            },
            {"title": "Section 2", "markdown": "Second half.", "activities": []},
        ],
    )
    fixed_activity = GeneratedMultipleChoiceActivity(
        question="2 + 2?", options=["3", "4"], correct_index=1
    )
    fix_calls = 0

    def fake_invoke(
        *, schema, messages, tier, model_config, purpose, calls, budget=None
    ):
        nonlocal fix_calls
        if schema is LessonContent:
            return broken
        if schema is GeneratedLessonActivityFix:
            fix_calls += 1
            return GeneratedLessonActivityFix(
                sections=[
                    GeneratedSectionActivities(
                        section_index=0, activities=[fixed_activity]
                    )
                ]
            )
        return EvaluationResult(passed=True, score=5, feedback="fine")

    with (
        patch.object(nodes, "invoke_structured", fake_invoke),
        patch.object(nodes, "solve_activities", return_value=[]),
    ):
        outcome = nodes.generate_lesson_content(
            overview=overview,
            unit=overview.units[0],
            outline=outline,
            lesson_index=0,
            course_map="Course map:",
            reading_style="single",
            model_config=MODEL_CONFIG,
        )

    assert outcome.passed is True
    assert fix_calls == 1
    assert outcome.content.sections[0].activities == [fixed_activity]
    assert outcome.content.sections[1].activities == []
    assert outcome.content.sections[1].markdown == "Second half."


def test_activity_fix_matches_by_index_not_by_position():
    """A section-count mismatch used to be matched by raw list position,
    which could silently apply one section's fix to a different section
    whenever the broken section wasn't first. Here the broken activity is
    in section 1 (not section 0), and the fix response - correctly -
    reports section_index=1. Section 0's own, already-fine activity must
    survive untouched."""
    from app.agent import nodes
    from tests.factories import make_lesson_content, make_outline, make_overview

    overview = make_overview()
    outline = make_outline(activity_types=["multipleChoice"])
    fine_activity = GeneratedMultipleChoiceActivity(
        question="1 + 1?", options=["2", "3"], correct_index=0
    )
    broken_activity = GeneratedMultipleChoiceActivity(
        question="2 + 2?", options=["3", "4"], correct_index=5
    )
    broken = make_lesson_content(
        markdown="# L",
        code_practice=None,
        sections=[
            {"title": "Section 1", "markdown": "fine", "activities": [fine_activity]},
            {
                "title": "Section 2",
                "markdown": "has the problem",
                "activities": [broken_activity],
            },
        ],
    )
    fixed_activity = GeneratedMultipleChoiceActivity(
        question="2 + 2?", options=["3", "4"], correct_index=1
    )

    def fake_invoke(
        *, schema, messages, tier, model_config, purpose, calls, budget=None
    ):
        if schema is LessonContent:
            return broken
        if schema is GeneratedLessonActivityFix:
            return GeneratedLessonActivityFix(
                sections=[
                    GeneratedSectionActivities(
                        section_index=1, activities=[fixed_activity]
                    )
                ]
            )
        return EvaluationResult(passed=True, score=5, feedback="fine")

    with (
        patch.object(nodes, "invoke_structured", fake_invoke),
        patch.object(nodes, "solve_activities", return_value=[]),
    ):
        outcome = nodes.generate_lesson_content(
            overview=overview,
            unit=overview.units[0],
            outline=outline,
            lesson_index=0,
            course_map="Course map:",
            reading_style="single",
            model_config=MODEL_CONFIG,
        )

    assert outcome.passed is True
    assert outcome.content.sections[0].activities == [fine_activity]
    assert outcome.content.sections[1].activities == [fixed_activity]


def test_an_out_of_range_section_index_in_the_fix_is_ignored():
    from app.agent import nodes
    from tests.factories import make_lesson_content, make_outline, make_overview

    overview = make_overview()
    outline = make_outline(activity_types=["multipleChoice"])
    broken = make_lesson_content(
        markdown="# L",
        code_practice=None,
        activities=[
            GeneratedMultipleChoiceActivity(
                question="2 + 2?", options=["3", "4"], correct_index=5
            )
        ],
    )
    fixed_activity = GeneratedMultipleChoiceActivity(
        question="2 + 2?", options=["3", "4"], correct_index=1
    )

    def fake_invoke(
        *, schema, messages, tier, model_config, purpose, calls, budget=None
    ):
        if schema is LessonContent:
            return broken
        if schema is GeneratedLessonActivityFix:
            return GeneratedLessonActivityFix(
                sections=[
                    GeneratedSectionActivities(
                        section_index=0, activities=[fixed_activity]
                    ),
                    GeneratedSectionActivities(
                        section_index=5, activities=[fixed_activity]
                    ),
                ]
            )
        return EvaluationResult(passed=True, score=5, feedback="fine")

    with (
        patch.object(nodes, "invoke_structured", fake_invoke),
        patch.object(nodes, "solve_activities", return_value=[]),
    ):
        outcome = nodes.generate_lesson_content(
            overview=overview,
            unit=overview.units[0],
            outline=outline,
            lesson_index=0,
            course_map="Course map:",
            reading_style="single",
            model_config=MODEL_CONFIG,
        )

    assert outcome.passed is True
    assert len(outcome.content.sections) == 1
    assert outcome.content.sections[0].activities == [fixed_activity]
