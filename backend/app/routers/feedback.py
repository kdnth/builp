import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import AuthenticatedUser, get_current_user, get_current_user_optional
from app.config import Settings, get_settings
from app.database import SessionLocal, get_db
from app.email import send_email
from app.models import Course as CourseModel
from app.models import FeedbackSubmission, Notification
from app.schemas.feedback import ContactRequest, CourseReportRequest, FeedbackResponse

router = APIRouter(prefix="/api/feedback", tags=["feedback"])

# The contact form is open to signed-out visitors, so it is the one endpoint
# here without an auth wall in front of it. Submissions are capped per IP
# over a rolling window to keep it from being used as a mail relay.
_RATE_LIMIT_WINDOW = timedelta(hours=1)
_RATE_LIMIT_MAX_SUBMISSIONS = 5

_CATEGORY_LABELS = {
    "incorrect_content": "Incorrect content",
    "broken_code_practice": "Broken code practice",
    "typo_or_formatting": "Typo or formatting",
    "inappropriate_content": "Inappropriate content",
    "other": "Other",
}


def _client_ip(request: Request) -> str | None:
    # Railway and Netlify both sit in front of this app, so the socket peer is
    # a proxy. The first X-Forwarded-For hop is the closest thing to the real
    # client. It is spoofable, which is fine for a coarse spam cap.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    return request.client.host if request.client else None


def _enforce_contact_rate_limit(*, db: Session, client_ip: str | None) -> None:
    if client_ip is None:
        return

    window_start = datetime.now(UTC) - _RATE_LIMIT_WINDOW
    recent = db.scalar(
        select(func.count())
        .select_from(FeedbackSubmission)
        .where(
            FeedbackSubmission.submitter_ip == client_ip,
            FeedbackSubmission.created_at >= window_start,
        )
    )
    if (recent or 0) >= _RATE_LIMIT_MAX_SUBMISSIONS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "That is a lot of messages in a short time. "
                "Try again in an hour, or email hello@kdnth.co directly."
            ),
        )


def _mark_delivered(db: Session, submission_id: str, delivered: bool) -> None:
    submission = db.get(FeedbackSubmission, submission_id)
    if submission is not None:
        submission.email_delivered = delivered
        db.commit()


@router.post(
    "/contact",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_contact(
    payload: ContactRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: AuthenticatedUser | None = Depends(get_current_user_optional),
) -> FeedbackResponse:
    client_ip = _client_ip(request)
    _enforce_contact_rate_limit(db=db, client_ip=client_ip)

    submission = FeedbackSubmission(
        id=str(uuid.uuid4()),
        kind="contact",
        subject=payload.subject,
        message=payload.message,
        submitter_user_id=user.id if user else None,
        submitter_name=payload.name,
        submitter_email=str(payload.email),
        submitter_ip=client_ip,
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    account = f"signed in as {user.id}" if user else "signed out"
    body = (
        f"From: {payload.name} <{payload.email}> ({account})\n"
        f"Subject: {payload.subject}\n\n"
        f"{payload.message}\n"
    )
    background_tasks.add_task(
        _send_and_record,
        submission_id=submission.id,
        settings=settings,
        to=settings.contact_email,
        subject=f"[builp contact] {payload.subject}",
        body=body,
        reply_to=str(payload.email),
    )
    return FeedbackResponse.model_validate(submission)


@router.post(
    "/courses/{course_id}/reports",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
)
def report_course_problem(
    course_id: str,
    payload: CourseReportRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: AuthenticatedUser = Depends(get_current_user),
) -> FeedbackResponse:
    course = db.get(CourseModel, course_id)
    if course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course not found."
        )

    category_label = _CATEGORY_LABELS.get(payload.category, payload.category)
    subject = f"{category_label} in \"{course.title}\""

    submission = FeedbackSubmission(
        id=str(uuid.uuid4()),
        kind="course_report",
        category=payload.category,
        subject=subject,
        message=payload.message,
        submitter_user_id=user.id,
        submitter_email=user.email,
        submitter_ip=_client_ip(request),
        course_id=course.id,
    )
    db.add(submission)

    # An authored course gets an in-app notification; an unowned one (seeded
    # or uploaded anonymously) has nobody to notify, and the support email
    # below is the only channel that matters for it.
    if course.owner_user_id and course.owner_user_id != user.id:
        lesson_hint = (
            f"\n\nReported against lesson: {payload.lesson_id}"
            if payload.lesson_id
            else ""
        )
        db.add(
            Notification(
                id=str(uuid.uuid4()),
                user_id=course.owner_user_id,
                kind="course_report",
                title=f"Problem reported in \"{course.title}\"",
                body=f"{category_label}: {payload.message}{lesson_hint}",
                link=f"/courses/{course.id}",
            )
        )

    db.commit()
    db.refresh(submission)

    reporter = user.email or user.id
    lesson_line = f"Lesson: {payload.lesson_id}\n" if payload.lesson_id else ""
    body = (
        f"Course: {course.title} ({course.id})\n"
        f"{settings.app_base_url}/courses/{course.id}\n"
        f"Author: {course.owner_user_id or 'none'}\n"
        f"Reported by: {reporter}\n"
        f"Category: {category_label}\n"
        f"{lesson_line}\n"
        f"{payload.message}\n"
    )
    background_tasks.add_task(
        _send_and_record,
        submission_id=submission.id,
        settings=settings,
        to=settings.support_email,
        subject=f"[builp report] {subject}",
        body=body,
        reply_to=user.email,
    )
    return FeedbackResponse.model_validate(submission)


def _send_and_record(
    *,
    submission_id: str,
    settings: Settings,
    to: str,
    subject: str,
    body: str,
    reply_to: str | None,
) -> None:
    """Runs after the response is sent. Opens its own session, since the
    request-scoped one from get_db is already closed by this point."""
    delivered = send_email(
        settings=settings,
        to=to,
        subject=subject,
        body=body,
        reply_to=reply_to,
    )
    with SessionLocal() as db:
        _mark_delivered(db, submission_id, delivered)
