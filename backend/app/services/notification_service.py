
from datetime import datetime, timezone
from typing import Any

from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.email_log import EmailDeliveryLog
from app.models.notification import Notification
from app.models.user import User
from app.services.email_service import (
    ALLOWED_TEMPLATES,
    deliver_email_log,
)


def publish_user_event(
    db: Session,
    background_tasks: BackgroundTasks,
    user_id: int,
    event_type: str,
    title: str,
    message: str,
    email_subject: str,
    template_name: str,
    context_data: dict[str, Any],
    extra_data: dict[str, Any] | None = None,
) -> Notification:
    """Create an in-app notification and queue a matching email."""

    user = db.get(User, user_id)

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active notification recipient not found",
        )

    if template_name not in ALLOWED_TEMPLATES:
        raise ValueError("Unsupported email template")

    notification = Notification(
        user_id=user.id,
        event_type=event_type,
        title=title,
        message=message,
        extra_data=extra_data or {},
    )

    email_log = EmailDeliveryLog(
        user_id=user.id,
        recipient_email=user.email,
        event_type=event_type,
        subject=email_subject,
        template_name=template_name,
        email_context=context_data,
        status="PENDING",
    )

    try:
        db.add(notification)
        db.add(email_log)
        db.flush()

        email_log_id = email_log.id

        db.commit()
        db.refresh(notification)

    except Exception:
        db.rollback()
        raise

    background_tasks.add_task(deliver_email_log, email_log_id)

    return notification


def list_user_notifications(
    db: Session,
    user_id: int,
    unread_only: bool = False,
    skip: int = 0,
    limit: int = 50,
) -> list[Notification]:
    statement = select(Notification).where(
        Notification.user_id == user_id
    )

    if unread_only:
        statement = statement.where(
            Notification.is_read.is_(False)
        )

    statement = (
        statement
        .order_by(Notification.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    return list(db.scalars(statement).all())


def count_unread_notifications(
    db: Session,
    user_id: int,
) -> int:
    count = db.scalar(
        select(func.count(Notification.id)).where(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
    )

    return int(count or 0)


def mark_notification_read(
    db: Session,
    user_id: int,
    notification_id: int,
) -> Notification:
    notification = db.get(Notification, notification_id)

    if notification is None or notification.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    if not notification.is_read:
        notification.is_read = True
        notification.read_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(notification)

    return notification


def mark_all_notifications_read(
    db: Session,
    user_id: int,
) -> int:
    notifications = db.scalars(
        select(Notification).where(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
    ).all()

    now = datetime.now(timezone.utc)

    for notification in notifications:
        notification.is_read = True
        notification.read_at = now

    db.commit()

    return len(notifications)


def list_email_delivery_logs(
    db: Session,
    status_filter: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[EmailDeliveryLog]:
    statement = select(EmailDeliveryLog)

    if status_filter:
        statement = statement.where(
            EmailDeliveryLog.status == status_filter
        )

    statement = (
        statement
        .order_by(EmailDeliveryLog.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    return list(db.scalars(statement).all())


def retry_email_delivery(
    db: Session,
    email_log_id: int,
    background_tasks: BackgroundTasks,
) -> EmailDeliveryLog:
    log = db.scalar(
        select(EmailDeliveryLog)
        .where(EmailDeliveryLog.id == email_log_id)
        .with_for_update()
    )

    if log is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email delivery log not found",
        )

    if log.status not in {"FAILED", "SKIPPED"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only failed or skipped emails can be retried",
        )

    log.status = "PENDING"
    log.error_message = None

    db.commit()
    db.refresh(log)

    background_tasks.add_task(deliver_email_log, log.id)

    return log
