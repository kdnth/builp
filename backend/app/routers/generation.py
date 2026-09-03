import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.agent.run import run_generation_job
from app.auth import AuthenticatedUser, get_current_user
from app.database import get_db
from app.models import GenerationJob
from app.schemas.generation import CreateGenerationJobRequest, GenerationJobResponse

router = APIRouter(prefix="/api/generation-jobs", tags=["generation"])

# Cost control: generation runs a chain of LLM calls per course. One
# request per rolling 24h window per user, regardless of whether that
# request succeeded, so a failing generation can't be retried into an
# unbounded bill.
_RATE_LIMIT_WINDOW = timedelta(hours=24)


@router.post(
    "", response_model=GenerationJobResponse, status_code=status.HTTP_201_CREATED
)
def create_generation_job(
    payload: CreateGenerationJobRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> GenerationJob:
    window_start = datetime.now(UTC) - _RATE_LIMIT_WINDOW
    recent_job = (
        db.query(GenerationJob)
        .filter(
            GenerationJob.owner_user_id == user.id,
            GenerationJob.created_at >= window_start,
        )
        .order_by(GenerationJob.created_at.desc())
        .first()
    )
    if recent_job is not None:
        retry_at = recent_job.created_at + _RATE_LIMIT_WINDOW
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "You've already generated a course in the last 24 hours. "
                f"Try again after {retry_at.isoformat()}."
            ),
        )

    job = GenerationJob(
        id=str(uuid.uuid4()),
        owner_user_id=user.id,
        status="pending",
        topic=payload.topic,
        audience=payload.audience,
        num_units=payload.num_units,
        lessons_per_unit=payload.lessons_per_unit,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(run_generation_job, job.id)
    return job


@router.get("/{job_id}", response_model=GenerationJobResponse)
def get_generation_job(
    job_id: str,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> GenerationJob:
    job = db.get(GenerationJob, job_id)
    if job is None or job.owner_user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Generation job not found."
        )
    return job
