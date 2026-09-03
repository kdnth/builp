from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr

JobStatus = Literal["pending", "running", "succeeded", "failed"]
GenerationMode = Literal["free_credit", "provider_api_key"]
SupportedProvider = Literal[
    "anthropic",
    "openai",
    "groq",
    "xai",
    "mistral",
    "gemini",
    "ollama",
    "deepseek",
]


class CreateGenerationJobRequest(BaseModel):
    topic: str = Field(min_length=1)
    audience: str = Field(min_length=1)
    num_units: int = Field(ge=1, le=10, default=3)
    lessons_per_unit: int = Field(ge=1, le=8, default=3)
    generation_mode: GenerationMode = "free_credit"
    provider: SupportedProvider | None = None
    provider_api_key: SecretStr | None = None


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
