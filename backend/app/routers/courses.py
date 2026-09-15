from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.auth import AuthenticatedUser, get_current_user, get_current_user_optional
from app.database import get_db
from app.models import Course as CourseModel
from app.models import LessonProgress as LessonProgressModel
from app.models import SavedCourse as SavedCourseModel
from app.schemas.course import (
    Course,
    CourseDetail,
    CourseSummary,
    PaginatedCourses,
    UpdateTagsRequest,
    summarize,
)

router = APIRouter(prefix="/api/courses", tags=["courses"])


def _saved_course_ids(db: Session, user_id: str) -> set[str]:
    return set(
        db.scalars(
            select(SavedCourseModel.course_id).where(
                SavedCourseModel.user_id == user_id
            )
        )
    )


def is_course_saved_by(db: Session, row: CourseModel, user_id: str) -> bool:
    if row.owner_user_id == user_id:
        return True
    return (
        db.scalar(
            select(SavedCourseModel).where(
                SavedCourseModel.user_id == user_id,
                SavedCourseModel.course_id == row.id,
            )
        )
        is not None
    )


@router.get("", response_model=PaginatedCourses)
def list_courses(
    q: str | None = None,
    tag: str | None = None,
    owner_user_id: str | None = None,
    for_user_id: str | None = None,
    limit: int = Query(24, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser | None = Depends(get_current_user_optional),
) -> PaginatedCourses:
    query = select(CourseModel)
    if q:
        query = query.where(CourseModel.title.ilike(f"%{q}%"))
    if owner_user_id:
        query = query.where(CourseModel.owner_user_id == owner_user_id)
    if for_user_id:
        saved_subquery = select(SavedCourseModel.course_id).where(
            SavedCourseModel.user_id == for_user_id
        )
        query = query.where(
            or_(
                CourseModel.owner_user_id == for_user_id,
                CourseModel.id.in_(saved_subquery),
            )
        )
    query = query.order_by(CourseModel.created_at.desc())

    saved_ids = (
        _saved_course_ids(db, current_user.id) if current_user is not None else set()
    )

    def _summarize(row: CourseModel) -> CourseSummary:
        saved = current_user is not None and (
            row.owner_user_id == current_user.id or row.id in saved_ids
        )
        return summarize(
            Course.model_validate(row.data),
            tags=row.tags,
            owner_user_id=row.owner_user_id,
            saved=saved,
        )

    if tag:
        summaries = [s for s in (_summarize(row) for row in db.scalars(query)) if tag in s.tags]
        total = len(summaries)
        items = summaries[offset : offset + limit]
    else:
        total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
        rows = db.scalars(query.offset(offset).limit(limit)).all()
        items = [_summarize(row) for row in rows]

    return PaginatedCourses(items=items, total=total)


@router.get("/{course_id}", response_model=CourseDetail)
def get_course(
    course_id: str,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser | None = Depends(get_current_user_optional),
) -> CourseDetail:
    row = db.get(CourseModel, course_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course not found."
        )
    saved = current_user is not None and is_course_saved_by(db, row, current_user.id)
    return CourseDetail.model_validate(
        {
            **row.data,
            "tags": row.tags,
            "owner_user_id": row.owner_user_id,
            "saved": saved,
        }
    )


@router.post("", response_model=CourseDetail, status_code=status.HTTP_201_CREATED)
def create_course(
    course: Course,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> CourseDetail:
    new_id = str(uuid4())
    forked_from_id = course.forkedFromId
    if forked_from_id is not None and db.get(CourseModel, forked_from_id) is None:
        forked_from_id = None

    content = {
        **course.model_dump(mode="json"),
        "id": new_id,
        "forkedFromId": forked_from_id,
    }
    row = CourseModel(
        id=new_id,
        title=course.title,
        data=content,
        owner_user_id=user.id,
        forked_from_id=forked_from_id,
        tags=[],
    )
    db.add(row)
    db.commit()
    return CourseDetail.model_validate(
        {**content, "tags": [], "owner_user_id": user.id, "saved": True}
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


    row.tags = sorted({t.strip() for t in payload.tags if t.strip()})
    db.commit()

    return summarize(
        Course.model_validate(row.data),
        tags=row.tags,
        owner_user_id=row.owner_user_id,
        saved=True,
    )


@router.post("/{course_id}/save", status_code=status.HTTP_204_NO_CONTENT)
def save_course(
    course_id: str,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> Response:
    row = db.get(CourseModel, course_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course not found."
        )
    if row.owner_user_id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already own this course.",
        )

    existing = db.scalar(
        select(SavedCourseModel).where(
            SavedCourseModel.user_id == user.id,
            SavedCourseModel.course_id == course_id,
        )
    )
    if existing is None:
        db.add(SavedCourseModel(user_id=user.id, course_id=course_id))
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{course_id}/save", status_code=status.HTTP_204_NO_CONTENT)
def unsave_course(
    course_id: str,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> Response:
    row = db.get(CourseModel, course_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course not found."
        )
    if row.owner_user_id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authors can't unsave their own courses. Delete it instead.",
        )

    existing = db.scalar(
        select(SavedCourseModel).where(
            SavedCourseModel.user_id == user.id,
            SavedCourseModel.course_id == course_id,
        )
    )
    if existing is not None:
        db.delete(existing)
    db.execute(
        delete(LessonProgressModel).where(
            LessonProgressModel.user_id == user.id,
            LessonProgressModel.course_id == course_id,
        )
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(
    course_id: str,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user)
    ) -> Response:
    row = db.get(CourseModel, course_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND
        )
    if row.owner_user_id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only the course's owner can delete a course.",
                )
    
    db.delete(row)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)