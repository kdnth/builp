import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth import AuthenticatedUser, get_current_user_optional
from app.main import app
from app.models import Course as CourseModel
from app.models import FeedbackSubmission, Notification


@pytest.fixture
def sent_emails(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    """Captures what the background task would have mailed, instead of
    letting it reach Resend."""
    captured: list[dict] = []

    def fake_send_email(*, settings, to, subject, body, reply_to=None) -> bool:
        captured.append(
            {"to": to, "subject": subject, "body": body, "reply_to": reply_to}
        )
        return True

    monkeypatch.setattr("app.routers.feedback.send_email", fake_send_email)
    return captured


def _contact_payload(**overrides) -> dict:
    payload = {
        "name": "Ada",
        "email": "ada@example.com",
        "subject": "Cannot sign in",
        "message": "The sign-in page keeps reloading.",
    }
    payload.update(overrides)
    return payload


def _make_course(db: Session, *, course_id: str, owner: str | None) -> CourseModel:
    course = CourseModel(
        id=course_id,
        title="Intro to Testing",
        data={"id": course_id, "title": "Intro to Testing", "units": []},
        owner_user_id=owner,
        tags=[],
    )
    db.add(course)
    db.commit()
    return course


# --- Contact form ------------------------------------------------------


def test_contact_stores_submission_and_emails_hello(
    client: TestClient, db_session: Session, sent_emails: list[dict]
) -> None:
    response = client.post("/api/feedback/contact", json=_contact_payload())

    assert response.status_code == 201
    assert response.json()["kind"] == "contact"

    row = db_session.query(FeedbackSubmission).one()
    assert row.kind == "contact"
    assert row.submitter_email == "ada@example.com"
    assert row.message == "The sign-in page keeps reloading."

    assert len(sent_emails) == 1
    assert sent_emails[0]["to"] == "hello@kdnth.co"
    assert sent_emails[0]["reply_to"] == "ada@example.com"
    assert "Cannot sign in" in sent_emails[0]["subject"]


def test_contact_works_for_signed_out_visitor(
    client: TestClient, db_session: Session, sent_emails: list[dict]
) -> None:
    app.dependency_overrides[get_current_user_optional] = lambda: None
    try:
        response = client.post("/api/feedback/contact", json=_contact_payload())
    finally:
        app.dependency_overrides.pop(get_current_user_optional, None)

    assert response.status_code == 201
    row = db_session.query(FeedbackSubmission).one()
    assert row.submitter_user_id is None


def test_contact_rejects_invalid_email(
    client: TestClient, sent_emails: list[dict]
) -> None:
    response = client.post(
        "/api/feedback/contact", json=_contact_payload(email="not-an-email")
    )

    assert response.status_code == 422
    assert sent_emails == []


def test_contact_rate_limits_by_ip(
    client: TestClient, db_session: Session, sent_emails: list[dict]
) -> None:
    headers = {"X-Forwarded-For": "203.0.113.7"}
    for _ in range(5):
        ok = client.post(
            "/api/feedback/contact", json=_contact_payload(), headers=headers
        )
        assert ok.status_code == 201

    blocked = client.post(
        "/api/feedback/contact", json=_contact_payload(), headers=headers
    )
    assert blocked.status_code == 429

    # A different client is unaffected by the first one's cap.
    other = client.post(
        "/api/feedback/contact",
        json=_contact_payload(),
        headers={"X-Forwarded-For": "198.51.100.4"},
    )
    assert other.status_code == 201
    assert db_session.query(FeedbackSubmission).count() == 6


# --- Course problem reports ---------------------------------------------


def test_report_notifies_author_and_emails_support(
    client: TestClient, db_session: Session, sent_emails: list[dict]
) -> None:
    _make_course(db_session, course_id="c1", owner="author-9")

    response = client.post(
        "/api/feedback/courses/c1/reports",
        json={
            "category": "broken_code_practice",
            "message": "The add() test suite expects the wrong output.",
            "lesson_id": "l1",
        },
    )

    assert response.status_code == 201

    notification = db_session.query(Notification).one()
    assert notification.user_id == "author-9"
    assert notification.kind == "course_report"
    assert notification.link == "/courses/c1"
    assert notification.read_at is None
    assert "Broken code practice" in notification.body
    assert "l1" in notification.body

    assert len(sent_emails) == 1
    assert sent_emails[0]["to"] == "support@kdnth.co"
    assert "Intro to Testing" in sent_emails[0]["body"]
    assert "author-9" in sent_emails[0]["body"]


def test_report_on_unowned_course_emails_without_notification(
    client: TestClient, db_session: Session, sent_emails: list[dict]
) -> None:
    _make_course(db_session, course_id="c2", owner=None)

    response = client.post(
        "/api/feedback/courses/c2/reports",
        json={"category": "other", "message": "A seeded course has a typo."},
    )

    assert response.status_code == 201
    assert db_session.query(Notification).count() == 0
    assert len(sent_emails) == 1
    assert sent_emails[0]["to"] == "support@kdnth.co"


def test_author_reporting_own_course_gets_no_self_notification(
    client: TestClient,
    db_session: Session,
    current_user: AuthenticatedUser,
    sent_emails: list[dict],
) -> None:
    _make_course(db_session, course_id="c3", owner=current_user.id)

    response = client.post(
        "/api/feedback/courses/c3/reports",
        json={"category": "typo_or_formatting", "message": "My own typo."},
    )

    assert response.status_code == 201
    assert db_session.query(Notification).count() == 0
    assert len(sent_emails) == 1


def test_report_on_missing_course_is_404(
    client: TestClient, db_session: Session, sent_emails: list[dict]
) -> None:
    response = client.post(
        "/api/feedback/courses/nope/reports",
        json={"category": "other", "message": "Where did it go?"},
    )

    assert response.status_code == 404
    assert db_session.query(FeedbackSubmission).count() == 0
    assert sent_emails == []


def test_report_rejects_empty_message(
    client: TestClient, sent_emails: list[dict]
) -> None:
    response = client.post(
        "/api/feedback/courses/c1/reports",
        json={"category": "other", "message": ""},
    )

    assert response.status_code == 422
    assert sent_emails == []


def test_failed_send_still_keeps_the_submission(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "app.routers.feedback.send_email",
        lambda **kwargs: False,
    )

    response = client.post("/api/feedback/contact", json=_contact_payload())

    assert response.status_code == 201
    row = db_session.query(FeedbackSubmission).one()
    assert row.email_delivered is False
