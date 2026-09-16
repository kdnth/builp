from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

ReportCategory = Literal[
    "incorrect_content",
    "broken_code_practice",
    "typo_or_formatting",
    "inappropriate_content",
    "other",
]


class ContactRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    subject: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=5000)


class CourseReportRequest(BaseModel):
    category: ReportCategory = "other"
    message: str = Field(min_length=1, max_length=5000)
    # Optional pointer at the part of the course the report is about.
    lesson_id: str | None = Field(default=None, max_length=200)


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    kind: str
    created_at: datetime
