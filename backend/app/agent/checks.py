"""Deterministic, non-LLM checks on generated content.

These run before the LLM-judge evaluator for a stage. They're free (no
model call) and catch objective bugs the judge shouldn't need to spend a
call re-discovering. If any of these fail, that's an automatic fail for
the stage with the problem list as regeneration feedback, and the judge
call is skipped entirely.
"""

import json
import re
import subprocess
import tempfile
from pathlib import Path

from app.agent.schemas import (
    CourseOverview,
    GeneratedFillBlankActivity,
    GeneratedFunctionPractice,
    GeneratedMultipleChoiceActivity,
    LessonContent,
    UnitOutline,
)


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


def check_function_practice_consistency(
    practice: GeneratedFunctionPractice,
) -> str | None:
    """Run `practice.reference_solution` against `practice.test_suite` in a
    Node subprocess. Returns None if it passes its own tests, or a problem
    description otherwise.

    A code practice whose own reference solution can't pass its test suite
    means the test suite is wrong, since a correct implementation should
    exist by construction. Worth catching before a lesson ships.
    """
    script = _NODE_CHECK_TEMPLATE % {
        "reference_solution": json.dumps(practice.reference_solution),
        "function_name": json.dumps(_function_name(practice.function_signature)),
        "test_cases": json.dumps(
            [
                {"input": tc.input, "expected_output": tc.expected_output}
                for tc in practice.test_suite
            ]
        ),
    }

    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
        f.write(script)
        script_path = f.name

    try:
        result = subprocess.run(
            ["node", script_path],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except FileNotFoundError:
        return None
    except subprocess.TimeoutExpired:
        return "reference solution timed out (possible infinite loop)"
    finally:
        Path(script_path).unlink(missing_ok=True)

    if result.returncode != 0:
        return f"reference solution crashed: {result.stderr.strip()[:500]}"

    try:
        outcome = json.loads(result.stdout.strip())
    except json.JSONDecodeError:
        return f"could not parse check output: {result.stdout[:500]}"

    return None if outcome.get("ok") else outcome.get("problem", "unknown problem")


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


def check_lesson_content(content: LessonContent) -> list[str]:
    """Every deterministic check applicable to a generated lesson.

    Returns a list of problems, empty if everything checks out.
    """
    problems: list[str] = []

    if content.code_practice is not None:
        problem = check_function_practice_consistency(content.code_practice)
        if problem:
            problems.append(problem)

    for activity in content.interactive_activities:
        if activity.type == "fillBlank":
            problem = check_fill_blank_consistency(activity)
        elif activity.type == "multipleChoice":
            problem = check_multiple_choice_consistency(activity)
        else:
            problem = None
        if problem:
            problems.append(problem)

    return problems
