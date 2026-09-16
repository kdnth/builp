"""Runs one generation job end to end and persists the result.

This is the function FastAPI's BackgroundTasks calls, after the request
that created the job has already returned. It opens its own DB session
(the request's session is gone by the time this runs) and is the only
place that moves a GenerationJob row from pending -> running ->
succeeded | failed.
"""

import logging

from sqlalchemy.orm import Session

from app.agent.graph import run_generation
from app.agent.llm import (
    CallUsage,
    GenerationModelConfig,
    default_free_credit_model_config,
)
from app.agent.metrics import (
    DatabaseMetricsReporter,
    StageMetrics,
    summarize_job_metrics,
)
from app.agent.progress import DatabaseProgressReporter
from app.agent.schemas import ScreeningDecision
from app.agent.screening import screen_topic
from app.database import SessionLocal
from app.models import Course as CourseModel
from app.models import GenerationJob

logger = logging.getLogger(__name__)


def _sanitize_error(message: str, *, secrets: list[str]) -> str:
    sanitized = message
    for secret in secrets:
        normalized = secret.strip()
        if normalized:
            sanitized = sanitized.replace(normalized, "[REDACTED]")
    return sanitized


def _job_metrics(db: Session, job_id: str) -> dict | None:
    try:
        return summarize_job_metrics(db, job_id)
    except Exception:
        logger.exception("Could not summarize metrics for job %s", job_id)
        return None


def _fail(
    db: Session,
    job: GenerationJob,
    exc: Exception,
    model_config: GenerationModelConfig,
) -> None:
    """The top-level job boundary: every failure, model error included, must
    land in the job row rather than crash a background thread silently."""
    job.status = "failed"
    job.error = _sanitize_error(str(exc), secrets=[model_config.api_key or ""])[:2000]
    job.metrics = _job_metrics(db, job.id)
    db.commit()


def _screen(
    job: GenerationJob,
    model_config: GenerationModelConfig,
    metrics: DatabaseMetricsReporter,
) -> ScreeningDecision:
    calls: list[CallUsage] = []
    try:
        return screen_topic(
            topic=job.topic,
            audience=job.audience,
            learning_goals=job.learning_goals,
            notes=job.notes,
            model_config=model_config,
            calls=calls,
        )
    finally:
        metrics.record_stage(
            StageMetrics(stage="screening", passed=True, attempts=1, calls=calls)
        )


def run_generation_job(
    job_id: str, model_config: GenerationModelConfig | None = None
) -> None:
    db = SessionLocal()
    active_model_config = model_config or default_free_credit_model_config()
    try:
        job = db.get(GenerationJob, job_id)
        if job is None:
            return

        job.status = "running"
        job.stage = "screening"
        job.lessons_total = job.num_units * job.lessons_per_unit
        job.lessons_completed = 0
        db.commit()

        metrics_reporter = DatabaseMetricsReporter(job.id, SessionLocal)
        try:
            decision = _screen(job, active_model_config, metrics_reporter)
        except Exception as exc:
            _fail(db, job, exc, active_model_config)
            return

        if not decision.allowed:
            job.status = "refused"
            job.refusal_category = decision.category
            job.refusal_reason = decision.reason
            job.metrics = _job_metrics(db, job.id)
            db.commit()
            return

        job.stage = "outline"
        db.commit()

        try:
            course = run_generation(
                topic=job.topic,
                audience=job.audience,
                num_units=job.num_units,
                lessons_per_unit=job.lessons_per_unit,
                course_type=job.course_type,
                language=job.language,
                level=job.level,
                learning_goals=job.learning_goals,
                notes=job.notes,
                reading_style=job.reading_style,
                model_config=active_model_config,
                progress=DatabaseProgressReporter(job.id, SessionLocal),
                metrics=metrics_reporter,
            )
        except Exception as exc:
            _fail(db, job, exc, active_model_config)
            return

        if db.get(CourseModel, course.id) is None:
            db.add(
                CourseModel(
                    id=course.id,
                    title=course.title,
                    course_type=course.courseType,
                    data=course.model_dump(mode="json"),
                    owner_user_id=job.owner_user_id,
                )
            )

        job.status = "succeeded"
        job.course_id = course.id
        job.metrics = _job_metrics(db, job.id)
        db.commit()
    finally:
        db.close()
