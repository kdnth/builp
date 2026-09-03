from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import AuthenticatedUser, get_current_user
from app.database import get_db
from app.models import Course as CourseModel
from app.schemas.course import Course, CourseSummary, summarize

router = APIRouter(prefix="/api/courses", tags=["courses"])


@router.get("", response_model=list[CourseSummary])
def list_courses(db: Session = Depends(get_db)) -> list[CourseSummary]:
    rows = db.scalars(select(CourseModel)).all()
    return [summarize(Course.model_validate(row.data)) for row in rows]


@router.get("/{course_id}", response_model=Course)
def get_course(course_id: str, db: Session = Depends(get_db)) -> Course:
    row = db.get(CourseModel, course_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course not found."
        )
    return Course.model_validate(row.data)


@router.post("", response_model=Course, status_code=status.HTTP_201_CREATED)
def create_course(
    course: Course,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> Course:
    if db.get(CourseModel, course.id) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f'A course with id "{course.id}" already exists.',
        )

    row = CourseModel(
        id=course.id,
        title=course.title,
        data=course.model_dump(mode="json"),
        owner_user_id=user.id,
    )
    db.add(row)
    db.commit()
    return course
