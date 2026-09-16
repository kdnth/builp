from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.auth import AuthenticatedUser, get_current_user
from app.database import get_db
from app.models import Notification
from app.schemas.notification import NotificationListResponse, NotificationResponse

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

# The bell is a dropdown, not an archive. It shows the newest slice and the
# full unread count, which is all the header needs.
_LIST_LIMIT = 30


@router.get("", response_model=NotificationListResponse)
def list_notifications(
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> NotificationListResponse:
    rows = db.scalars(
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(_LIST_LIMIT)
    ).all()
    unread_count = db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user.id, Notification.read_at.is_(None))
    )
    return NotificationListResponse(
        items=[NotificationResponse.model_validate(row) for row in rows],
        unread_count=unread_count or 0,
    )


@router.post("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: str,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> NotificationResponse:
    row = db.get(Notification, notification_id)
    # Someone else's notification reads as missing rather than forbidden, so
    # the endpoint never confirms that an id exists.
    if row is None or row.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found."
        )
    if row.read_at is None:
        row.read_at = datetime.now(UTC)
        db.commit()
        db.refresh(row)
    return NotificationResponse.model_validate(row)


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> Response:
    db.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.read_at.is_(None))
        .values(read_at=datetime.now(UTC))
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
