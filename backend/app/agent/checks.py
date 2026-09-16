"""Deterministic, non-LLM checks on generated content.

These run before the LLM-judge evaluator for a stage. They're free (no
model call) and catch objective bugs the judge shouldn't need to spend a
call re-discovering. If any of these fail, that's an automatic fail for
the stage with the problem list as regeneration feedback, and the judge
call is skipped entirely.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from app.agent.activity_checks import (
    check_activity_grounding,
    check_fill_blank_answerability,
    check_multiple_choice_quality,
)
from app.agent.schemas import (
    CodePracticePolicy,
    CourseBrief,
    CourseOverview,
    GeneratedFillBlankActivity,
    GeneratedFunctionPractice,
    GeneratedMultipleChoiceActivity,
    LessonContent,
    UnitOutline,
)
from app.schemas.course import CodeLanguage


def check_overview_unit_count(overview: CourseOverview, expected: int) -> list[str]:
    """The model tends to treat a requested unit count as a suggestion, not
    a requirement, if nothing forces the point. Nothing in CourseOverview's
    own schema can enforce an exact length, since it varies per request, so
    this is enforced here instead."""
    if len(overview.units) != expected:
        return [
            f"produced {len(overview.units)} units, but exactly {expected} "
            "were requested. Add or remove units to match exactly."
        ]
    return []


def check_outline_lesson_count(outline: UnitOutline, expected: int) -> list[str]:
    if len(outline.lessons) != expected:
        return [
            f"produced {len(outline.lessons)} lessons, but exactly {expected} "
            "were requested. Add or remove lessons to match exactly."
        ]
    return []


def check_outline_lessons(outline: UnitOutline, brief: CourseBrief) -> list[str]:
    """Each lesson must use a profile the brief allows, and a course with no
    code practice must not ask for one."""
    problems: list[str] = []
    for index, lesson in enumerate(outline.lessons, start=1):
        if lesson.profile not in brief.lesson_profiles:
            problems.append(
                f"lesson {index} uses profile '{lesson.profile}', which is not "
                f"one of the course's profiles "
                f"({', '.join(brief.lesson_profiles)})"
            )
        if lesson.include_code_practice and brief.code_practice_policy == "none":
            problems.append(
                f"lesson {index} asks for a code practice, but this course has "
                "no code practice"
            )
    return problems


def _function_name(signature: str) -> str:
    match = re.match(r"^\s*([a-zA-Z_$][\w$]*)\s*\(", signature)
    return match.group(1) if match else signature.strip()


_NODE_CHECK_TEMPLATE = """
const referenceSolution = %(reference_solution)s;
const functionName = %(function_name)s;
const testCases = %(test_cases)s;

let fn;
try {
  fn = new Function(referenceSolution + "\\nreturn " + functionName + ";")();
} catch (err) {
  const parseProblem = "reference solution does not parse: " + err.message;
  console.log(JSON.stringify({ ok: false, problem: parseProblem }));
  process.exit(0);
}

const mismatches = [];
for (const [index, testCase] of testCases.entries()) {
  try {
    const actual = fn(...testCase.input);
    const args = JSON.stringify(testCase.input).slice(1, -1);
    const expected = JSON.stringify(testCase.expected_output);
    if (JSON.stringify(actual) !== expected) {
      mismatches.push(
        "test " + index + ": " + functionName + "(" + args + ") returned " +
        JSON.stringify(actual) + ", expected " + expected
      );
    }
  } catch (err) {
    mismatches.push("test " + index + " threw: " + err.message);
  }
}

if (mismatches.length > 0) {
  const joined = mismatches.join("; ");
  const problem = "reference solution fails its own test suite: " + joined;
  console.log(JSON.stringify({ ok: false, problem }));
} else {
  console.log(JSON.stringify({ ok: true }));
}
"""


_PYTHON_CHECK_TEMPLATE = """
import json

reference_solution = %(reference_solution)s
function_name = %(function_name)s
test_cases = json.loads(%(test_cases)s)


def report(ok, problem=None):
    print()
    print(json.dumps({"ok": ok, "problem": problem}))
    raise SystemExit(0)


def canonical(value):
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, (list, tuple)):
        return [canonical(item) for item in value]
    if isinstance(value, dict):
        return {key: canonical(item) for key, item in value.items()}
    return value


def encode(value):
    return json.dumps(
        canonical(value), separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


namespace = {"__name__": "__main__"}
try:
    exec(compile(reference_solution, "<solution>", "exec"), namespace)
except SyntaxError as exc:
    report(False, f"reference solution does not parse: {exc}")
except Exception as exc:
    report(False, f"reference solution raised on load: {type(exc).__name__}: {exc}")

fn = namespace.get(function_name)
if not callable(fn):
    report(False, f"reference solution does not define a function {function_name}")

mismatches = []
for index, case in enumerate(test_cases):
    call = f"{function_name}({json.dumps(case['input'])[1:-1]})"
    try:
        actual = fn(*case["input"])
    except Exception as exc:
        mismatches.append(f"test {index} raised {type(exc).__name__}: {exc}")
        continue
    try:
        actual_json = encode(actual)
    except (TypeError, ValueError):
        mismatches.append(
            f"test {index}: {call} returned {actual!r}, which is not JSON "
            "serializable (return a number, string, bool, None, list, or dict)"
        )
        continue
    expected_json = encode(case["expected_output"])
    if actual_json != expected_json:
        mismatches.append(
            f"test {index}: {call} returned {actual_json}, expected {expected_json}"
        )

if mismatches:
    report(
        False, "reference solution fails its own test suite: " + "; ".join(mismatches)
    )
report(True)
"""

CHECK_TIMEOUT_SECONDS = 5


def _run_check_script(command: list[str], script: str, suffix: str) -> str | None:
    with tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False) as f:
        f.write(script)
        script_path = f.name

    try:
        result = subprocess.run(
            [*command, script_path],
            capture_output=True,
            text=True,
            timeout=CHECK_TIMEOUT_SECONDS,
            env={"PATH": os.environ.get("PATH", "")},
        )
    except FileNotFoundError:
        return (
            f"the {command[0]} runtime is not installed on the server, so the "
            "reference solution could not be checked"
        )
    except subprocess.TimeoutExpired:
        return "reference solution timed out (possible infinite loop)"
    finally:
        Path(script_path).unlink(missing_ok=True)

    if result.returncode != 0:
        return f"reference solution crashed: {result.stderr.strip()[:500]}"

    lines = result.stdout.strip().splitlines()
    try:
        outcome = json.loads(lines[-1])
    except (IndexError, json.JSONDecodeError):
        return f"could not parse check output: {result.stdout[:500]}"

    return None if outcome.get("ok") else outcome.get("problem", "unknown problem")


def check_function_practice_consistency(
    practice: GeneratedFunctionPractice, *, language: CodeLanguage
) -> str | None:
    """Run `practice.reference_solution` against `practice.test_suite` in a
    Node or Python subprocess. Returns None if it passes its own tests, or a
    problem description otherwise.

    A code practice whose own reference solution can't pass its test suite
    means the test suite is wrong, since a correct implementation should
    exist by construction. Worth catching before a lesson ships.
    """
    function_name = _function_name(practice.function_signature)
    test_cases = [
        {"input": tc.input, "expected_output": tc.expected_output}
        for tc in practice.test_suite
    ]

    if language == "python":
        script = _PYTHON_CHECK_TEMPLATE % {
            "reference_solution": repr(practice.reference_solution),
            "function_name": repr(function_name),
            "test_cases": repr(json.dumps(test_cases)),
        }
        return _run_check_script([sys.executable, "-I"], script, ".py")

    script = _NODE_CHECK_TEMPLATE % {
        "reference_solution": json.dumps(practice.reference_solution),
        "function_name": json.dumps(function_name),
        "test_cases": json.dumps(test_cases),
    }
    return _run_check_script(["node"], script, ".js")


def check_fill_blank_consistency(activity: GeneratedFillBlankActivity) -> str | None:
    blank_count = activity.text.count("{{blank}}")
    if blank_count != len(activity.blanks):
        return (
            f"text has {blank_count} {{{{blank}}}} tokens but blanks has "
            f"{len(activity.blanks)} entries"
        )
    return None


def check_multiple_choice_consistency(
    activity: GeneratedMultipleChoiceActivity,
) -> str | None:
    if not 0 <= activity.correct_index < len(activity.options):
        return (
            f"correct_index {activity.correct_index} is out of range for "
            f"{len(activity.options)} options"
        )
    return None


def check_lesson_content(
    content: LessonContent, *, language: CodePracticePolicy
) -> list[str]:
    """Every deterministic check applicable to a generated lesson.

    Returns a list of problems, empty if everything checks out.
    """
    problems: list[str] = []

    if content.code_practice is not None:
        if language == "none":
            problems.append(
                "this lesson has a code practice, but this lesson was asked "
                "not to have one"
            )
        else:
            problem = check_function_practice_consistency(
                content.code_practice, language=language
            )
            if problem:
                problems.append(problem)

    for activity in content.interactive_activities:
        if activity.type == "fillBlank":
            problem = check_fill_blank_consistency(activity)
            problems.extend(check_fill_blank_answerability(activity))
        elif activity.type == "multipleChoice":
            problem = check_multiple_choice_consistency(activity)
            problems.extend(check_multiple_choice_quality(activity))
        else:
            problem = None
        if problem:
            problems.append(problem)
        problems.extend(
            check_activity_grounding(activity, content.written_lesson_markdown)
        )

    return problems
