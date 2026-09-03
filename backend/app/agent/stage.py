"""The generate -> check -> evaluate -> retry-with-feedback loop.

This is deliberately plain Python, not a LangGraph subgraph. Retrying a
single stage doesn't need graph-level cycles, checkpointing, or
interruption; it's a bounded loop with a clear exit condition. LangGraph is
used one level up, in graph.py, for the part that actually needs graph
structure: fanning out over units and lessons in parallel and reducing the
results back together.

Kept generic (and LLM-agnostic via plain callables) so the retry and
tier-escalation behavior can be unit tested with stub functions, without a
model call or an API key.
"""

from collections.abc import Callable
from dataclasses import dataclass, field

from app.agent.llm import ModelTier, tier_for_attempt
from app.agent.schemas import EvaluationResult


@dataclass
class StageAttempt[T]:
    attempt: int
    tier: ModelTier
    content: T
    problems: list[str]
    evaluation: EvaluationResult | None


@dataclass
class StageOutcome[T]:
    content: T
    passed: bool
    attempts: list[StageAttempt[T]] = field(default_factory=list)

    @property
    def attempt_count(self) -> int:
        return len(self.attempts)


def run_stage_with_retries[T](
    *,
    generate: Callable[[ModelTier, str | None], T],
    check: Callable[[T], list[str]],
    evaluate: Callable[[T], EvaluationResult],
    default_tier: ModelTier,
    max_attempts: int = 3,
) -> StageOutcome[T]:
    """Run one stage's generate/check/evaluate loop.

    `generate(tier, feedback)` produces a candidate. `feedback` is None on
    the first attempt, and the previous attempt's problem description on
    every retry, so the model gets a real shot at fixing what was wrong.

    `check` is the free, deterministic pass (schema-shape and internal
    consistency checks). If it finds problems, `evaluate` is skipped
    entirely for that attempt, since there's no point paying for an LLM
    judge call on content that's already known to be broken.

    `evaluate` only runs once `check` passes, and is the LLM-as-judge call
    for the stage's qualitative rubric.

    The last attempt (`max_attempts`) always uses the `strong` tier,
    regardless of `default_tier` (see `tier_for_attempt`), as a quality
    backstop. The loop always returns something: even if the final attempt
    still fails, its content is returned with `passed=False` so the caller
    can decide how to handle a stage that never cleared the bar (used as
    written, flagged for human review, etc.) rather than crashing the job.

    `generate` and `evaluate` are both LLM calls, and both can raise: a
    model occasionally returns a nested object JSON-encoded as a string
    instead of structured output, which fails Pydantic validation deep
    inside the call. Losing an entire stage (and, one level up in
    graph.py, every sibling unit or lesson generated alongside it) to one
    bad call would be a bad trade for a bounded, already-retrying loop, so
    an exception here is treated the same as a failed check: it becomes
    feedback for the next attempt. Only if every attempt raises, including
    the final strong-tier one, does the exception actually propagate.
    """
    attempts: list[StageAttempt[T]] = []
    feedback: str | None = None
    last_error: Exception | None = None

    for attempt_number in range(1, max_attempts + 1):
        tier = tier_for_attempt(default_tier, attempt_number, max_attempts)

        try:
            content = generate(tier, feedback)
        except Exception as exc:  # noqa: BLE001 - see docstring
            last_error = exc
            feedback = f"Your last response could not be read: {exc}"
            continue

        problems = check(content)

        if problems:
            feedback = "Fix these problems: " + "; ".join(problems)
            attempts.append(
                StageAttempt(
                    attempt=attempt_number,
                    tier=tier,
                    content=content,
                    problems=problems,
                    evaluation=None,
                )
            )
            continue

        try:
            evaluation = evaluate(content)
        except Exception as exc:  # noqa: BLE001 - see docstring
            last_error = exc
            feedback = f"Your last response could not be read: {exc}"
            attempts.append(
                StageAttempt(
                    attempt=attempt_number,
                    tier=tier,
                    content=content,
                    problems=[],
                    evaluation=None,
                )
            )
            continue

        attempts.append(
            StageAttempt(
                attempt=attempt_number,
                tier=tier,
                content=content,
                problems=[],
                evaluation=evaluation,
            )
        )

        if evaluation.passed:
            return StageOutcome(content=content, passed=True, attempts=attempts)

        feedback = evaluation.feedback

    if attempts:
        return StageOutcome(
            content=attempts[-1].content, passed=False, attempts=attempts
        )

    assert last_error is not None  # every loop iteration sets one or the other
    raise last_error
