"""Per-stage generation metrics.

Every stage run records one row: how many attempts it needed, what the
deterministic checks found, what the judge scored, and how many tokens it
used. Parallel branches each insert their own row, so there is nothing to
merge while a job runs. run.py writes the job summary once at the end.

These numbers are the input for two open decisions in
docs/plans/non-programming-courses.md: whether to split lesson generation
into separate calls, and whether a lesson profile needs its own generator.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.llm import CallUsage
from app.agent.stage import StageOutcome
from app.models import GenerationStageMetric

logger = logging.getLogger(__name__)

StageName = Literal["overview", "unit_outline", "lesson_content"]


@dataclass
class StageMetrics:
    stage: StageName
    passed: bool
    attempts: int
    detail: list[dict[str, object]] = field(default_factory=list)
    calls: list[CallUsage] = field(default_factory=list)

    def totals(self) -> dict[str, int]:
        return {
            "input_tokens": sum(call.input_tokens for call in self.calls),
            "output_tokens": sum(call.output_tokens for call in self.calls),
            "cache_read_tokens": sum(call.cache_read_tokens for call in self.calls),
            "cache_creation_tokens": sum(
                call.cache_creation_tokens for call in self.calls
            ),
        }


def stage_metrics(stage: StageName, outcome: StageOutcome) -> StageMetrics:
    detail = [
        {
            "attempt": attempt.attempt,
            "tier": attempt.tier,
            "problems": attempt.problems,
            "score": attempt.evaluation.score if attempt.evaluation else None,
            "passed": bool(attempt.evaluation and attempt.evaluation.passed),
        }
        for attempt in outcome.attempts
    ]
    return StageMetrics(
        stage=stage,
        passed=outcome.passed,
        attempts=outcome.attempt_count,
        detail=detail,
        calls=outcome.calls,
    )


class MetricsReporter(Protocol):
    def record_stage(self, metrics: StageMetrics) -> None: ...


class NoopMetricsReporter:
    def record_stage(self, metrics: StageMetrics) -> None:
        pass


class DatabaseMetricsReporter:
    def __init__(self, job_id: str, session_factory: Callable[[], Session]):
        self._job_id = job_id
        self._session_factory = session_factory

    def record_stage(self, metrics: StageMetrics) -> None:
        # Measurement must never fail a generation job.
        try:
            totals = metrics.totals()
            with self._session_factory() as db:
                db.add(
                    GenerationStageMetric(
                        job_id=self._job_id,
                        stage=metrics.stage,
                        passed=metrics.passed,
                        attempts=metrics.attempts,
                        detail={
                            "attempts": metrics.detail,
                            "calls": [call.as_dict() for call in metrics.calls],
                        },
                        **totals,
                    )
                )
                db.commit()
        except Exception:
            logger.exception("Could not record stage metrics for job %s", self._job_id)


def summarize_job_metrics(db: Session, job_id: str) -> dict[str, object]:
    """Roll the stage rows of one job into a summary for `generation_jobs`."""
    rows = db.scalars(
        select(GenerationStageMetric).where(GenerationStageMetric.job_id == job_id)
    ).all()

    stages: dict[str, dict[str, int]] = {}
    calls: dict[str, int] = {}
    tokens = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_tokens": 0,
        "cache_creation_tokens": 0,
    }

    for row in rows:
        stage = stages.setdefault(
            row.stage, {"runs": 0, "attempts": 0, "not_passed": 0}
        )
        stage["runs"] += 1
        stage["attempts"] += row.attempts
        if not row.passed:
            stage["not_passed"] += 1

        for call in (row.detail or {}).get("calls", []):
            purpose = str(call.get("purpose", "unknown"))
            calls[purpose] = calls.get(purpose, 0) + 1

        for key in tokens:
            tokens[key] += getattr(row, key)

    return {
        "stages": stages,
        "calls": calls,
        "tokens": tokens,
        "recorded_at": datetime.now(UTC).isoformat(),
    }
