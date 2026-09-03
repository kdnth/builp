import pytest

from app.agent.schemas import EvaluationResult
from app.agent.stage import run_stage_with_retries


def _eval(passed: bool, feedback: str = "") -> EvaluationResult:
    return EvaluationResult(passed=passed, score=5 if passed else 2, feedback=feedback)


def test_passes_on_first_attempt_without_retrying():
    generate_calls = []

    def generate(tier, feedback):
        generate_calls.append((tier, feedback))
        return "draft-1"

    outcome = run_stage_with_retries(
        generate=generate,
        check=lambda content: [],
        evaluate=lambda content: _eval(True),
        default_tier="fast",
    )

    assert outcome.passed is True
    assert outcome.content == "draft-1"
    assert outcome.attempt_count == 1
    assert generate_calls == [("fast", None)]


def test_retries_with_evaluator_feedback_then_passes():
    generate_calls = []

    def generate(tier, feedback):
        generate_calls.append((tier, feedback))
        return f"draft-{len(generate_calls)}"

    evaluate_calls = {"n": 0}

    def evaluate(content):
        evaluate_calls["n"] += 1
        if evaluate_calls["n"] == 1:
            return _eval(False, feedback="too short")
        return _eval(True)

    outcome = run_stage_with_retries(
        generate=generate,
        check=lambda content: [],
        evaluate=evaluate,
        default_tier="fast",
        max_attempts=3,
    )

    assert outcome.passed is True
    assert outcome.attempt_count == 2
    assert generate_calls[0] == ("fast", None)
    assert generate_calls[1] == ("fast", "too short")


def test_deterministic_check_failure_skips_evaluator_call():
    evaluate_calls = []

    def generate(tier, feedback):
        return "bad-content"

    def check(content):
        return ["blank count mismatch"]

    outcome = run_stage_with_retries(
        generate=generate,
        check=check,
        evaluate=lambda content: evaluate_calls.append(content) or _eval(True),
        default_tier="fast",
        max_attempts=2,
    )

    # evaluate should never run: every attempt fails the free check first
    assert evaluate_calls == []
    assert outcome.passed is False
    assert outcome.attempt_count == 2


def test_check_feedback_is_fed_into_next_generate_call():
    feedback_seen = []

    def generate(tier, feedback):
        feedback_seen.append(feedback)
        return "content"

    def check(content):
        # fail once, then pass
        return ["missing X"] if len(feedback_seen) == 1 else []

    run_stage_with_retries(
        generate=generate,
        check=check,
        evaluate=lambda content: _eval(True),
        default_tier="fast",
        max_attempts=3,
    )

    assert feedback_seen[0] is None
    assert "missing X" in feedback_seen[1]


def test_final_attempt_escalates_to_strong_tier():
    tiers_used = []

    def generate(tier, feedback):
        tiers_used.append(tier)
        return "content"

    run_stage_with_retries(
        generate=generate,
        check=lambda content: [],
        evaluate=lambda content: _eval(False, feedback="still bad"),
        default_tier="fast",
        max_attempts=3,
    )

    assert tiers_used == ["fast", "fast", "strong"]


def test_never_escalates_below_max_attempts():
    tiers_used = []

    def generate(tier, feedback):
        tiers_used.append(tier)
        return "content"

    run_stage_with_retries(
        generate=generate,
        check=lambda content: [],
        evaluate=lambda content: _eval(False, feedback="bad"),
        default_tier="standard",
        max_attempts=3,
    )

    assert tiers_used == ["standard", "standard", "strong"]


def test_returns_last_attempt_content_when_never_passes():
    def generate(tier, feedback):
        return f"tier={tier}"

    outcome = run_stage_with_retries(
        generate=generate,
        check=lambda content: [],
        evaluate=lambda content: _eval(False, feedback="nope"),
        default_tier="fast",
        max_attempts=2,
    )

    assert outcome.passed is False
    assert outcome.content == "tier=strong"
    assert outcome.attempt_count == 2


def test_max_attempts_of_one_never_retries():
    calls = []

    def generate(tier, feedback):
        calls.append(feedback)
        return "content"

    outcome = run_stage_with_retries(
        generate=generate,
        check=lambda content: [],
        evaluate=lambda content: _eval(False, feedback="bad"),
        default_tier="fast",
        max_attempts=1,
    )

    assert len(calls) == 1
    assert outcome.passed is False


def test_generate_exception_is_retried_with_feedback():
    calls = []

    def generate(tier, feedback):
        calls.append(feedback)
        if len(calls) == 1:
            raise ValueError("model returned a stringified object, not JSON")
        return "content"

    outcome = run_stage_with_retries(
        generate=generate,
        check=lambda content: [],
        evaluate=lambda content: _eval(True),
        default_tier="fast",
        max_attempts=3,
    )

    assert outcome.passed is True
    assert calls[0] is None
    assert "stringified object" in calls[1]


def test_generate_exception_on_every_attempt_reraises():
    def generate(tier, feedback):
        raise ValueError("still broken")

    with pytest.raises(ValueError, match="still broken"):
        run_stage_with_retries(
            generate=generate,
            check=lambda content: [],
            evaluate=lambda content: _eval(True),
            default_tier="fast",
            max_attempts=3,
        )


def test_evaluate_exception_is_retried_with_feedback():
    generate_calls = []
    evaluate_calls = []

    def generate(tier, feedback):
        generate_calls.append(feedback)
        return f"draft-{len(generate_calls)}"

    def evaluate(content):
        evaluate_calls.append(content)
        if len(evaluate_calls) == 1:
            raise ValueError("judge response did not parse")
        return _eval(True)

    outcome = run_stage_with_retries(
        generate=generate,
        check=lambda content: [],
        evaluate=evaluate,
        default_tier="fast",
        max_attempts=3,
    )

    assert outcome.passed is True
    assert outcome.content == "draft-2"
    assert "judge response did not parse" in generate_calls[1]


def test_generate_exception_does_not_escalate_tier_early():
    tiers_used = []

    def generate(tier, feedback):
        tiers_used.append(tier)
        raise ValueError("boom")

    with pytest.raises(ValueError):
        run_stage_with_retries(
            generate=generate,
            check=lambda content: [],
            evaluate=lambda content: _eval(True),
            default_tier="fast",
            max_attempts=3,
        )

    # still escalates on the final attempt, same as any other failure
    assert tiers_used == ["fast", "fast", "strong"]
