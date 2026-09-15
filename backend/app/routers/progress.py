from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import AuthenticatedUser, get_current_user
from app.database import get_db
from app.models import Course as CourseModel
from app.models import LessonProgress
from app.routers.courses import is_course_saved_by
from app.schemas.progress import LessonCompleteResponse, ProgressResponse

router = APIRouter(prefix="/api/courses/{course_id}/progress", tags=["progress"])


def _ensure_course_exists(db: Session, course_id: str) -> CourseModel:
    row = db.get(CourseModel, course_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course not found."
        )
    return row


@router.get("", response_model=ProgressResponse)
def get_progress(
    course_id: str,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> ProgressResponse:
    _ensure_course_exists(db, course_id)
    rows = db.scalars(
        select(LessonProgress).where(
            LessonProgress.user_id == user.id,
            LessonProgress.course_id == course_id,
        )
    ).all()
    return ProgressResponse(
        course_id=course_id,
        completed_lesson_ids=[row.lesson_id for row in rows],
    )


@router.post("/lessons/{lesson_id}/complete", response_model=LessonCompleteResponse)
def complete_lesson(
    course_id: str,
    lesson_id: str,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> LessonCompleteResponse:
    course = _ensure_course_exists(db, course_id)
    if not is_course_saved_by(db, course, user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Save this course to My Courses before you make progress on it.",
        )

    existing = db.scalar(
        select(LessonProgress).where(
            LessonProgress.user_id == user.id,
            LessonProgress.course_id == course_id,
            LessonProgress.lesson_id == lesson_id,
        )
    )
    if existing is not None:
        return LessonCompleteResponse(
            course_id=course_id,
            lesson_id=lesson_id,
            completed_at=existing.completed_at,
        )

    row = LessonProgress(user_id=user.id, course_id=course_id, lesson_id=lesson_id)
    db.add(row)
    db.commit()
    db.refresh(row)
    return LessonCompleteResponse(
        course_id=course_id, lesson_id=lesson_id, completed_at=row.completed_at
    )
