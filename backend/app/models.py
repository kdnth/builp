from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
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


class FeedbackSubmission(Base):
    """A contact message, or a problem report against one course. This is the
    durable record of what someone submitted, kept whether or not the
    notification email reached an inbox."""

    __tablename__ = "feedback_submissions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    kind: Mapped[str] = mapped_column(String, nullable=False, index=True)
    category: Mapped[str | None] = mapped_column(String, nullable=True)
    subject: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Null when a signed-out visitor uses the contact form.
    submitter_user_id: Mapped[str | None] = mapped_column(String, nullable=True)
    submitter_name: Mapped[str | None] = mapped_column(String, nullable=True)
    submitter_email: Mapped[str | None] = mapped_column(String, nullable=True)
    # Rate limiting only. See app/routers/feedback.py.
    submitter_ip: Mapped[str | None] = mapped_column(String, nullable=True, index=True)

    course_id: Mapped[str | None] = mapped_column(
        ForeignKey("courses.id", ondelete="SET NULL"), nullable=True
    )
    email_delivered: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True
    )


class Notification(Base):
    """An in-app message for one user, read through the header bell."""

    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    # Relative app path the bell entry links to, e.g. /courses/abc123.
    link: Mapped[str | None] = mapped_column(String, nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True
    )
