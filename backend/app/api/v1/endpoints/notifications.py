
from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.permissions import require_permissions
from app.models.user import User
from app.schemas.notification import (
    EmailDeliveryLogRead,
    MarkReadResponse,
    NotificationRead,
    UnreadNotificationCount,
)
from app.services.notification_service import (
    count_unread_notifications,
    list_email_delivery_logs,
    list_user_notifications,
    mark_all_notifications_read,
    mark_notification_read,
    retry_email_delivery,
)


router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
)


@router.get(
    "/me",
    response_model=list[NotificationRead],
)
def read_my_notifications(
    unread_only: bool = False,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permissions("NOTIFICATIONS.READ_SELF")
    ),
):
    return list_user_notifications(
        db,
        current_user.id,
        unread_only,
        skip,
        limit,
    )


@router.get(
    "/me/unread-count",
    response_model=UnreadNotificationCount,
)
def read_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permissions("NOTIFICATIONS.READ_SELF")
    ),
):
    return UnreadNotificationCount(
        unread_count=count_unread_notifications(
            db,
            current_user.id,
        )
    )


@router.post(
    "/me/read-all",
    response_model=MarkReadResponse,
)
def read_all_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permissions("NOTIFICATIONS.UPDATE_SELF")
    ),
):
    count = mark_all_notifications_read(
        db,
        current_user.id,
    )

    return MarkReadResponse(
        message="Notifications marked as read",
        updated_count=count,
    )


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationRead,
)
def mark_one_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permissions("NOTIFICATIONS.UPDATE_SELF")
    ),
):
    return mark_notification_read(
        db,
        current_user.id,
        notification_id,
    )


@router.get(
    "/admin/email-logs",
    response_model=list[EmailDeliveryLogRead],
)
def read_email_logs(
    status_filter: str | None = Query(
        default=None,
        pattern="^(PENDING|SENT|FAILED|SKIPPED)$",
    ),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    _current_user: User = Depends(
        require_permissions("NOTIFICATIONS.EMAIL_LOGS_READ")
    ),
):
    return list_email_delivery_logs(
        db,
        status_filter,
        skip,
        limit,
    )


@router.post(
    "/admin/email-logs/{email_log_id}/retry",
    response_model=EmailDeliveryLogRead,
)
def retry_email_log(
    email_log_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _current_user: User = Depends(
        require_permissions("NOTIFICATIONS.EMAIL_RETRY")
    ),
):
    return retry_email_delivery(
        db,
        email_log_id,
        background_tasks,
    )
