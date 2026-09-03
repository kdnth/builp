import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.agent.llm import GenerationModelConfig, default_free_credit_model_config
from app.agent.run import run_generation_job
from app.auth import AuthenticatedUser, get_current_user
from app.database import get_db
from app.models import GenerationJob
from app.schemas.generation import CreateGenerationJobRequest, GenerationJobResponse

router = APIRouter(prefix="/api/generation-jobs", tags=["generation"])

# Cost control for the server-funded free-credit path: generation runs a
# chain of LLM calls per course, so free_credit mode is limited to one
# request per rolling 24h window per user (regardless of success/failure)
# to prevent retry loops from becoming unbounded cost.
_RATE_LIMIT_WINDOW = timedelta(hours=24)


def _enforce_free_credit_rate_limit(*, db: Session, user: AuthenticatedUser) -> None:
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
    if recent_job is None:
        return

    retry_at = recent_job.created_at + _RATE_LIMIT_WINDOW
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=(
            "You've already generated a course in the last 24 hours. "
            f"Try again after {retry_at.isoformat()}."
        ),
    )


def _resolve_model_config(
    payload: CreateGenerationJobRequest,
) -> tuple[GenerationModelConfig, bool]:
    if payload.generation_mode == "free_credit":
        if payload.provider is not None or payload.provider_api_key is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Do not send provider credentials when using free_credit mode.",
            )
        return default_free_credit_model_config(), True

    if payload.provider is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="provider is required when generation_mode is provider_api_key.",
        )

    if payload.provider_api_key is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "provider_api_key is required when generation_mode is "
                "provider_api_key."
            ),
        )

    api_key = payload.provider_api_key.get_secret_value().strip()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "provider_api_key is required when generation_mode is "
                "provider_api_key."
            ),
        )

    return GenerationModelConfig(provider=payload.provider, api_key=api_key), False


@router.post(
    "", response_model=GenerationJobResponse, status_code=status.HTTP_201_CREATED
)
def create_generation_job(
    payload: CreateGenerationJobRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> GenerationJob:
    model_config, uses_free_credit = _resolve_model_config(payload)
    if uses_free_credit:
        _enforce_free_credit_rate_limit(db=db, user=user)

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

    # model_config is passed in-memory to the background task only.
    background_tasks.add_task(run_generation_job, job.id, model_config)
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
