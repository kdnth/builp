from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import AuthenticatedUser, get_current_user
from app.database import get_db
from app.models import Course as CourseModel
from app.schemas.course import (
    Course,
    CourseDetail,
    CourseSummary,
    UpdateTagsRequest,
    summarize,
)

router = APIRouter(prefix="/api/courses", tags=["courses"])


@router.get("", response_model=list[CourseSummary])
def list_courses(
    q: str | None = None,
    tag: str | None = None,
    db: Session = Depends(get_db),
) -> list[CourseSummary]:
    query = select(CourseModel)
    if q:
        query = query.where(CourseModel.title.ilike(f"%{q}%"))
    rows = db.scalars(query).all()

    summaries = [
        summarize(
            Course.model_validate(row.data),
            tags=row.tags,
            owner_user_id=row.owner_user_id,
        )
        for row in rows
    ]

    if tag:
        summaries = [s for s in summaries if tag in s.tags]

    return summaries


@router.get("/{course_id}", response_model=CourseDetail)
def get_course(course_id: str, db: Session = Depends(get_db)) -> CourseDetail:
    row = db.get(CourseModel, course_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course not found."
        )
    return CourseDetail.model_validate(
        {**row.data, "tags": row.tags, "owner_user_id": row.owner_user_id}
    )


@router.post("", response_model=CourseDetail, status_code=status.HTTP_201_CREATED)
def create_course(
    course: Course,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> CourseDetail:
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
        tags=[],
    )
    db.add(row)
    db.commit()
    return CourseDetail.model_validate(
        {**course.model_dump(), "tags": [], "owner_user_id": user.id}
    )


@router.patch("/{course_id}/tags", response_model=CourseSummary)
def update_course_tags(
    course_id: str,
    payload: UpdateTagsRequest,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> CourseSummary:
    row = db.get(CourseModel, course_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course not found."
        )
    if row.owner_user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the course's author can change its tags.",
        )

    # Dedupe and drop blanks, but otherwise leave tags free-form: no fixed
    # taxonomy to maintain for a v1 tagging feature.
    row.tags = sorted({t.strip() for t in payload.tags if t.strip()})
    db.commit()

    return summarize(
        Course.model_validate(row.data), tags=row.tags, owner_user_id=row.owner_user_id
    )
