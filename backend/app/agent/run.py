"""Runs one generation job end to end and persists the result.

This is the function FastAPI's BackgroundTasks calls, after the request
that created the job has already returned. It opens its own DB session
(the request's session is gone by the time this runs) and is the only
place that moves a GenerationJob row from pending -> running ->
succeeded | failed.
"""

from app.agent.graph import run_generation
from app.database import SessionLocal
from app.models import Course as CourseModel
from app.models import GenerationJob


def run_generation_job(job_id: str) -> None:
    db = SessionLocal()
    try:
        job = db.get(GenerationJob, job_id)
        if job is None:
            return

        job.status = "running"
        db.commit()

        try:
            course = run_generation(
                topic=job.topic,
                audience=job.audience,
                num_units=job.num_units,
                lessons_per_unit=job.lessons_per_unit,
            )
        except Exception as exc:
            # This is the top-level job boundary: every failure, model
            # error included, must land in the job row rather than crash
            # a background thread silently.
            job.status = "failed"
            job.error = str(exc)[:2000]
            db.commit()
            return

        if db.get(CourseModel, course.id) is None:
            db.add(
                CourseModel(
                    id=course.id,
                    title=course.title,
                    data=course.model_dump(mode="json"),
                    owner_user_id=job.owner_user_id,
                )
            )

        job.status = "succeeded"
        job.course_id = course.id
        db.commit()
    finally:
        db.close()
