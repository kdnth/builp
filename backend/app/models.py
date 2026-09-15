from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    data: Mapped[dict] = mapped_column(JSON, nullable=False)
    owner_user_id: Mapped[str | None] = mapped_column(String, nullable=True)
    tags: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list, server_default="[]"
    )
    forked_from_id: Mapped[str | None] = mapped_column(
        ForeignKey("courses.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class SavedCourse(Base):
    """A course bookmarked into a user's "My Courses" list without owning
    it. Membership in My Courses is owner_user_id == user OR a row here -
    an author's own courses are never rowed here (see save_course), since
    ownership alone already guarantees membership."""

    __tablename__ = "saved_courses"

    user_id: Mapped[str] = mapped_column(String, primary_key=True)
                                         
    course_id: Mapped[str] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )


class LessonProgress(Base):
    __tablename__ = "lesson_progress"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "course_id", "lesson_id", name="uq_user_course_lesson"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    course_id: Mapped[str] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )
    lesson_id: Mapped[str] = mapped_column(String, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )


class GenerationJob(Base):
    __tablename__ = "generation_jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    topic: Mapped[str] = mapped_column(String, nullable=False)
    audience: Mapped[str] = mapped_column(String, nullable=False)
    num_units: Mapped[int] = mapped_column(Integer, nullable=False)
    lessons_per_unit: Mapped[int] = mapped_column(Integer, nullable=False)
    language: Mapped[str] = mapped_column(
        String, nullable=False, default="javascript", server_default="javascript"
    )
    stage: Mapped[str | None] = mapped_column(String, nullable=True)
    lessons_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lessons_completed: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
      
    course_id: Mapped[str | None] = mapped_column(
        ForeignKey("courses.id", ondelete="SET NULL"), nullable=True
    )
    error: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class GenerationStageMetric(Base):
    """One row per stage run of a generation job. See app/agent/metrics.py."""

    __tablename__ = "generation_stage_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[str] = mapped_column(
        ForeignKey("generation_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage: Mapped[str] = mapped_column(String, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cache_read_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cache_creation_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    detail: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
