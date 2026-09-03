from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

JobStatus = Literal["pending", "running", "succeeded", "failed"]


class CreateGenerationJobRequest(BaseModel):
    topic: str = Field(min_length=1)
    audience: str = Field(min_length=1)
    num_units: int = Field(ge=1, le=10, default=3)
    lessons_per_unit: int = Field(ge=1, le=8, default=3)


class GenerationJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: JobStatus
    topic: str
    audience: str
    num_units: int
    lessons_per_unit: int
    course_id: str | None
    error: str | None
    created_at: datetime
    updated_at: datetime
