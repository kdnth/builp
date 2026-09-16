from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth import AuthenticatedUser
from app.models import Notification


def _add_notification(
    db: Session,
    *,
    notification_id: str,
    user_id: str,
    title: str = "Problem reported",
    created_at: datetime | None = None,
    read_at: datetime | None = None,
) -> Notification:
    row = Notification(
        id=notification_id,
        user_id=user_id,
        kind="course_report",
        title=title,
        body="Something is wrong.",
        link="/courses/c1",
        read_at=read_at,
        created_at=created_at or datetime.now(UTC),
    )
    db.add(row)
    db.commit()
    return row


def test_list_returns_only_own_notifications_newest_first(
    client: TestClient, db_session: Session, current_user: AuthenticatedUser
) -> None:
    now = datetime.now(UTC)
    _add_notification(
        db_session,
        notification_id="n-old",
        user_id=current_user.id,
        title="Older",
        created_at=now - timedelta(hours=2),
    )
    _add_notification(
        db_session,
        notification_id="n-new",
        user_id=current_user.id,
        title="Newer",
        created_at=now,
    )
    _add_notification(
        db_session, notification_id="n-other", user_id="someone-else"
    )

    response = client.get("/api/notifications")

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body["items"]] == ["n-new", "n-old"]
    assert body["unread_count"] == 2


def test_unread_count_excludes_read_rows(
    client: TestClient, db_session: Session, current_user: AuthenticatedUser
) -> None:
    _add_notification(db_session, notification_id="n1", user_id=current_user.id)
    _add_notification(
        db_session,
        notification_id="n2",
        user_id=current_user.id,
        read_at=datetime.now(UTC),
    )

    body = client.get("/api/notifications").json()

    assert len(body["items"]) == 2
    assert body["unread_count"] == 1


def test_mark_read_sets_timestamp_once(
    client: TestClient, db_session: Session, current_user: AuthenticatedUser
) -> None:
    _add_notification(db_session, notification_id="n1", user_id=current_user.id)

    first = client.post("/api/notifications/n1/read")
    assert first.status_code == 200
    read_at = first.json()["read_at"]
    assert read_at is not None

    # A second call is a no-op rather than a fresh timestamp.
    second = client.post("/api/notifications/n1/read")
    assert second.status_code == 200
    assert second.json()["read_at"] == read_at


def test_mark_read_on_another_users_notification_is_404(
    client: TestClient, db_session: Session
) -> None:
    _add_notification(db_session, notification_id="n1", user_id="someone-else")

    response = client.post("/api/notifications/n1/read")

    assert response.status_code == 404
    db_session.expire_all()
    assert db_session.get(Notification, "n1").read_at is None


def test_read_all_clears_only_own_unread(
    client: TestClient, db_session: Session, current_user: AuthenticatedUser
) -> None:
    _add_notification(db_session, notification_id="n1", user_id=current_user.id)
    _add_notification(db_session, notification_id="n2", user_id=current_user.id)
    _add_notification(db_session, notification_id="n3", user_id="someone-else")

    response = client.post("/api/notifications/read-all")

    assert response.status_code == 204
    assert client.get("/api/notifications").json()["unread_count"] == 0
    db_session.expire_all()
    assert db_session.get(Notification, "n3").read_at is None
