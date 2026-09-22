from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator

from app.schemas.course import CourseType

JobStatus = Literal["pending", "running", "succeeded", "failed", "refused"]
GenerationStage = Literal["screening", "outline", "units", "lessons", "assembling"]
# "auto" lets the model decide, "none" forbids code practice entirely.
CodePracticeChoice = Literal["javascript", "python", "none", "auto"]
LearnerLevel = Literal["beginner", "intermediate", "advanced"]
ReadingStyle = Literal["single", "interleaved"]
MAX_CONTEXT_FIELD_LENGTH = 1000
GenerationMode = Literal["free_credit", "provider_api_key"]
SupportedProvider = Literal["anthropic"]


class CreateGenerationJobRequest(BaseModel):
    topic: str = Field(min_length=1)
    audience: str = Field(min_length=1)
    num_units: int = Field(ge=1, le=10, default=3)
    lessons_per_unit: int = Field(ge=1, le=8, default=3)
    course_type: CourseType = "programming"
    language: CodePracticeChoice | None = None
    learning_goals: str | None = Field(
        default=None, max_length=MAX_CONTEXT_FIELD_LENGTH
    )
    level: LearnerLevel = "beginner"
    notes: str | None = Field(default=None, max_length=MAX_CONTEXT_FIELD_LENGTH)
    reading_style: ReadingStyle | None = None
    generation_mode: GenerationMode = "free_credit"
    provider: SupportedProvider | None = None
    provider_api_key: SecretStr | None = None

    @model_validator(mode="after")
    def _defaults_per_course_type(self) -> "CreateGenerationJobRequest":
        """A programming course needs a real language. A general course lets
        the model decide, and reads with quick checks by default."""
        if self.course_type == "programming":
            if self.language is None:
                self.language = "javascript"
            elif self.language in ("none", "auto"):
                raise ValueError(
                    "A programming course needs language javascript or python."
                )
            if self.reading_style is None:
                self.reading_style = "single"
        else:
            if self.language is None:
                self.language = "auto"
            if self.reading_style is None:
                self.reading_style = "interleaved"
        return self


class GenerationJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: JobStatus
    topic: str
    audience: str
    num_units: int
    lessons_per_unit: int
    course_type: CourseType
    language: CodePracticeChoice
    learning_goals: str | None
    level: LearnerLevel
    notes: str | None
    reading_style: ReadingStyle
    stage: GenerationStage | None
    lessons_total: int | None
    lessons_completed: int
    course_id: str | None
    error: str | None
    refusal_category: str | None
    refusal_reason: str | None
    created_at: datetime
    updated_at: datetime
