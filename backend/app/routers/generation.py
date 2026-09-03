import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.agent.run import run_generation_job
from app.auth import AuthenticatedUser, get_current_user
from app.database import get_db
from app.models import GenerationJob
from app.schemas.generation import CreateGenerationJobRequest, GenerationJobResponse

router = APIRouter(prefix="/api/generation-jobs", tags=["generation"])


@router.post(
    "", response_model=GenerationJobResponse, status_code=status.HTTP_201_CREATED
)
def create_generation_job(
    payload: CreateGenerationJobRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> GenerationJob:
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
