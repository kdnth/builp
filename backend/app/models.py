from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, UniqueConstraint
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
    # DB-side metadata, deliberately not part of the course JSON content
    # (data above). A course uploaded or generated before tags existed
    # just gets the column default: [], no backfill needed.
    tags: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list, server_default="[]"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
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
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id"), nullable=False)
    lesson_id: Mapped[str] = mapped_column(String, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )


class GenerationJob(Base):
    __tablename__ = "generation_jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    # pending -> running -> succeeded | failed
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    topic: Mapped[str] = mapped_column(String, nullable=False)
    audience: Mapped[str] = mapped_column(String, nullable=False)
    num_units: Mapped[int] = mapped_column(Integer, nullable=False)
    lessons_per_unit: Mapped[int] = mapped_column(Integer, nullable=False)
    course_id: Mapped[str | None] = mapped_column(
        ForeignKey("courses.id"), nullable=True
    )
    error: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )
