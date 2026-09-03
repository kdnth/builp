from datetime import datetime

from pydantic import BaseModel


class ProgressResponse(BaseModel):
    course_id: str
    completed_lesson_ids: list[str]


class LessonCompleteResponse(BaseModel):
    course_id: str
    lesson_id: str
    completed_at: datetime
