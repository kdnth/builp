from app.agent.checks import (
    check_fill_blank_consistency,
    check_function_practice_consistency,
    check_lesson_content,
    check_multiple_choice_consistency,
    check_outline_lesson_count,
    check_overview_unit_count,
)
from app.agent.schemas import (
    CourseOverview,
    GeneratedFillBlankActivity,
    GeneratedFunctionPractice,
    GeneratedMultipleChoiceActivity,
    GeneratedTestCase,
    LessonContent,
    LessonSummary,
    UnitOutline,
    UnitSummary,
)


def _practice(reference_solution: str, cases: list[tuple[list[object], object]]):
    return GeneratedFunctionPractice(
        title="Add",
        function_signature="add(a, b)",
        description="Add two numbers.",
        reference_solution=reference_solution,
        test_suite=[
            GeneratedTestCase(input=inp, expected_output=out) for inp, out in cases
        ],
    )


def test_function_practice_consistency_passes_for_correct_solution():
    practice = _practice(
        "function add(a, b) { return a + b }", [([1, 2], 3), ([5, 5], 10)]
    )
    assert check_function_practice_consistency(practice, language="javascript") is None


def test_function_practice_consistency_catches_wrong_expected_output():
    practice = _practice(
        "function add(a, b) { return a + b }", [([1, 2], 999), ([5, 5], 10)]
    )
    problem = check_function_practice_consistency(practice, language="javascript")
    assert problem is not None
    assert "fails its own test suite" in problem


def test_function_practice_consistency_catches_syntax_error():
    practice = _practice(
        "function add(a, b { return a + b }", [([1, 2], 3), ([5, 5], 10)]
    )
    problem = check_function_practice_consistency(practice, language="javascript")
    assert problem is not None
    assert "does not parse" in problem


def _python_practice(
    reference_solution: str,
    cases: list[tuple[list[object], object]],
    function_signature: str = "add(a, b)",
):
    return GeneratedFunctionPractice(
        title="Practice",
        function_signature=function_signature,
        description="A practice.",
        reference_solution=reference_solution,
        test_suite=[
            GeneratedTestCase(input=inp, expected_output=out) for inp, out in cases
        ],
    )


def test_python_consistency_passes_for_correct_solution():
    practice = _python_practice(
        "def add(a, b):\n    return a + b", [([1, 2], 3), ([5, 5], 10)]
    )
    assert check_function_practice_consistency(practice, language="python") is None


def test_python_consistency_catches_wrong_expected_output():
    practice = _python_practice(
        "def add(a, b):\n    return a + b", [([1, 2], 999), ([5, 5], 10)]
    )
    problem = check_function_practice_consistency(practice, language="python")
    assert problem is not None
    assert "fails its own test suite" in problem
    assert "add(1, 2) returned 3, expected 999" in problem


def test_python_consistency_catches_syntax_error():
    practice = _python_practice(
        "def add(a, b)\n    return a + b", [([1, 2], 3), ([5, 5], 10)]
    )
    problem = check_function_practice_consistency(practice, language="python")
    assert problem is not None
    assert "does not parse" in problem


def test_python_consistency_catches_missing_function():
    practice = _python_practice(
        "def plus(a, b):\n    return a + b", [([1, 2], 3), ([5, 5], 10)]
    )
    problem = check_function_practice_consistency(practice, language="python")
    assert problem is not None
    assert "does not define a function add" in problem


def test_python_consistency_compares_like_the_browser_runner():
    practice = _python_practice(
        "def stats(values):\n"
        "    print('debug output', values)\n"
        "    return {'mean': sum(values) / len(values), 'pair': (1, 2)}",
        [
            ([[1, 2, 3]], {"mean": 2, "pair": [1, 2]}),
            ([[1, 2]], {"mean": 1.5, "pair": [1, 2]}),
        ],
        function_signature="stats(values)",
    )
    assert check_function_practice_consistency(practice, language="python") is None


def test_python_consistency_catches_dict_key_order_and_sets():
    key_order = _python_practice(
        "def f():\n    return {'b': 1, 'a': 2}",
        [([], {"a": 2, "b": 1}), ([], {"a": 2, "b": 1})],
        function_signature="f()",
    )
    assert check_function_practice_consistency(key_order, language="python")

    returns_set = _python_practice(
        "def f():\n    return {1, 2}",
        [([], [1, 2]), ([], [1, 2])],
        function_signature="f()",
    )
    problem = check_function_practice_consistency(returns_set, language="python")
    assert problem is not None
    assert "not JSON serializable" in problem


def test_python_consistency_times_out_on_infinite_loop(monkeypatch):
    monkeypatch.setattr("app.agent.checks.CHECK_TIMEOUT_SECONDS", 1)
    practice = _python_practice(
        "def add(a, b):\n    while True:\n        pass", [([1, 2], 3), ([5, 5], 10)]
    )
    problem = check_function_practice_consistency(practice, language="python")
    assert problem is not None
    assert "timed out" in problem


def test_consistency_check_does_not_expose_server_environment(monkeypatch):
    monkeypatch.setenv("CHECK_TEST_SECRET", "do-not-leak")
    practice = _python_practice(
        "import os\ndef add(a, b):\n    return os.environ.get('CHECK_TEST_SECRET')",
        [([1, 2], None), ([5, 5], None)],
    )
    assert check_function_practice_consistency(practice, language="python") is None


def test_check_lesson_content_uses_the_requested_language():
    content = LessonContent(
        written_lesson_markdown="# hi",
        code_practice=_python_practice(
            "def add(a, b):\n    return a + b", [([1, 2], 3), ([5, 5], 10)]
        ),
        interactive_activities=[],
    )
    assert check_lesson_content(content, language="python") == []
    assert len(check_lesson_content(content, language="javascript")) == 1


def test_fill_blank_consistency_ok():
    activity = GeneratedFillBlankActivity(
        text="{{blank}} is a {{blank}} language.",
        blanks=[{"accepted": ["Python"]}, {"accepted": ["scripting"]}],
    )
    assert check_fill_blank_consistency(activity) is None


def test_fill_blank_consistency_catches_mismatch():
    activity = GeneratedFillBlankActivity(
        text="{{blank}} is a {{blank}} language.",
        blanks=[{"accepted": ["Python"]}],
    )
    problem = check_fill_blank_consistency(activity)
    assert problem is not None
    assert "2" in problem and "1" in problem


def test_multiple_choice_consistency_ok():
    activity = GeneratedMultipleChoiceActivity(
        question="2 + 2?", options=["3", "4"], correct_index=1
    )
    assert check_multiple_choice_consistency(activity) is None


def test_multiple_choice_consistency_catches_out_of_range():
    activity = GeneratedMultipleChoiceActivity(
        question="2 + 2?", options=["3", "4"], correct_index=5
    )
    assert check_multiple_choice_consistency(activity) is not None


def test_check_lesson_content_aggregates_all_problems():
    content = LessonContent(
        written_lesson_markdown="# hi",
        code_practice=_practice(
            "function add(a, b) { return a + b }", [([1, 2], 999), ([5, 5], 10)]
        ),
        interactive_activities=[
            GeneratedMultipleChoiceActivity(
                question="2 + 2?", options=["3", "4"], correct_index=5
            ),
        ],
    )
    problems = check_lesson_content(content, language="javascript")
    assert len(problems) == 2


def test_check_lesson_content_empty_when_clean():
    content = LessonContent(
        written_lesson_markdown="# hi",
        code_practice=None,
        interactive_activities=[
            GeneratedMultipleChoiceActivity(
                question="2 + 2?", options=["3", "4"], correct_index=1
            ),
        ],
    )
    assert check_lesson_content(content, language="javascript") == []


def _overview(num_units: int) -> CourseOverview:
    return CourseOverview(
        title="Course",
        description="A course.",
        audience="Everyone.",
        units=[
            UnitSummary(title=f"Unit {i + 1}", goal="Goal.") for i in range(num_units)
        ],
    )


def test_overview_unit_count_matches():
    assert check_overview_unit_count(_overview(3), expected=3) == []


def test_overview_unit_count_mismatch():
    problems = check_overview_unit_count(_overview(5), expected=1)
    assert len(problems) == 1
    assert "5" in problems[0] and "1" in problems[0]


def _outline(num_lessons: int) -> UnitOutline:
    return UnitOutline(
        lessons=[
            LessonSummary(
                title=f"Lesson {i + 1}",
                goal="Goal.",
                include_code_practice=False,
                interactive_activity_types=[],
            )
            for i in range(num_lessons)
        ]
    )


def test_outline_lesson_count_matches():
    assert check_outline_lesson_count(_outline(2), expected=2) == []


def test_outline_lesson_count_mismatch():
    problems = check_outline_lesson_count(_outline(4), expected=1)
    assert len(problems) == 1
    assert "4" in problems[0] and "1" in problems[0]
