
from datetime import datetime, timezone
from typing import Any

from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.department import Department
from app.models.employee import Employee
from app.models.email_log import EmailDeliveryLog
from app.models.notification import Notification
from app.models.notification_preference import NotificationPreference
from app.models.user import User
from app.schemas.notification import (
    NotificationBroadcastCreate,
    NotificationBroadcastResponse,
    NotificationPreferenceUpdate,
)
from app.services.email_service import (
    ALLOWED_TEMPLATES,
    deliver_email_log,
)


def _get_or_create_preferences(
    db: Session,
    user_id: int,
) -> NotificationPreference:
    """Return existing preferences or create enabled-by-default settings."""
    user = db.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    preference = db.scalar(
        select(NotificationPreference).where(
            NotificationPreference.user_id == user_id
        )
    )

    if preference is not None:
        return preference

    preference = NotificationPreference(user_id=user_id)
    db.add(preference)

    try:
        db.commit()
        db.refresh(preference)
        return preference
    except IntegrityError:
        db.rollback()

        preference = db.scalar(
            select(NotificationPreference).where(
                NotificationPreference.user_id == user_id
            )
        )

        if preference is not None:
            return preference

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to initialize notification preferences",
        ) from None


def get_notification_preferences(
    db: Session,
    user_id: int,
) -> NotificationPreference:
    return _get_or_create_preferences(db, user_id)


def update_notification_preferences(
    db: Session,
    user_id: int,
    payload: NotificationPreferenceUpdate,
) -> NotificationPreference:
    """Update only preference fields included in the request."""
    changes = payload.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least one preference to update",
        )

    if any(value is None for value in changes.values()):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Preference values must be true or false",
        )

    preference = _get_or_create_preferences(db, user_id)

    for field, value in changes.items():
        setattr(preference, field, value)

    try:
        db.commit()
        db.refresh(preference)
        return preference
    except Exception:
        db.rollback()
        raise


def _get_preference_field(event_type: str) -> str:
    """Map a notification event to its preference category."""
    normalized = event_type.strip().upper()

    if "LEAVE" in normalized:
        return "leave_updates_enabled"

    if "PAYROLL" in normalized or "SALARY" in normalized:
        return "payroll_updates_enabled"

    if "ATTENDANCE" in normalized:
        return "attendance_alerts_enabled"

    if (
        "ANNOUNCEMENT" in normalized
        or "BROADCAST" in normalized
    ):
        return "announcements_enabled"

    return "other_updates_enabled"


def _is_in_app_notification_enabled(
    db: Session,
    user_id: int,
    event_type: str,
) -> bool:
    preference = db.scalar(
        select(NotificationPreference).where(
            NotificationPreference.user_id == user_id
        )
    )

    # Existing users without preferences retain enabled-by-default behavior.
    if preference is None:
        return True

    if not preference.in_app_enabled:
        return False

    return bool(
        getattr(
            preference,
            _get_preference_field(event_type),
        )
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
) -> Notification | None:
    """
    Preserve the email workflow while respecting in-app preferences.
    """
    user = db.get(User, user_id)

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active notification recipient not found",
        )

    if template_name not in ALLOWED_TEMPLATES:
        raise ValueError("Unsupported email template")

    notification = None

    if _is_in_app_notification_enabled(
        db,
        user.id,
        event_type,
    ):
        notification = Notification(
            user_id=user.id,
            event_type=event_type,
            title=title,
            message=message,
            extra_data=extra_data or {},
        )
        db.add(notification)

    # Email delivery is independent of in-app preferences.
    email_log = EmailDeliveryLog(
        user_id=user.id,
        recipient_email=user.email,
        event_type=event_type,
        subject=email_subject,
        template_name=template_name,
        email_context=context_data,
        status="PENDING",
    )
    db.add(email_log)

    try:
        db.flush()
        email_log_id = email_log.id
        db.commit()

        if notification is not None:
            db.refresh(notification)
    except Exception:
        db.rollback()
        raise

    background_tasks.add_task(deliver_email_log, email_log_id)

    return notification


def broadcast_notification(
    db: Session,
    actor_user_id: int,
    payload: NotificationBroadcastCreate,
) -> NotificationBroadcastResponse:
    """
    Broadcast an in-app announcement to active users or selected departments.

    Each recipient receives an independent Notification record.
    User preferences are respected, and this function does not send emails.
    """
    if payload.scope == "DEPARTMENTS":
        requested_ids = set(payload.department_ids)

        active_department_ids = set(
            db.scalars(
                select(Department.id).where(
                    Department.id.in_(requested_ids),
                    Department.is_active.is_(True),
                )
            ).all()
        )

        if active_department_ids != requested_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "One or more selected departments do not exist "
                    "or are inactive"
                ),
            )

        target_statement = (
            select(User)
            .join(Employee, Employee.user_id == User.id)
            .where(
                User.is_active.is_(True),
                Employee.employment_status == "ACTIVE",
                Employee.department_id.in_(requested_ids),
            )
            .order_by(User.id)
        )
    else:
        # Organization-wide announcements include active user accounts.
        target_statement = (
            select(User)
            .where(User.is_active.is_(True))
            .order_by(User.id)
        )

    target_users = list(
        db.scalars(target_statement).all()
    )

    target_user_ids = [user.id for user in target_users]

    preferences_by_user: dict[int, NotificationPreference] = {}

    if target_user_ids:
        preferences = db.scalars(
            select(NotificationPreference).where(
                NotificationPreference.user_id.in_(target_user_ids)
            )
        ).all()

        preferences_by_user = {
            preference.user_id: preference
            for preference in preferences
        }

    notifications: list[Notification] = []

    for user in target_users:
        preference = preferences_by_user.get(user.id)

        # No preference record means enabled by default.
        if preference is not None:
            if (
                not preference.in_app_enabled
                or not preference.announcements_enabled
            ):
                continue

        notifications.append(
            Notification(
                user_id=user.id,
                event_type="ADMIN_ANNOUNCEMENT",
                title=payload.title,
                message=payload.message,
                extra_data={
                    "scope": payload.scope,
                    "department_ids": (
                        payload.department_ids
                        if payload.scope == "DEPARTMENTS"
                        else []
                    ),
                    "sent_by_user_id": actor_user_id,
                },
            )
        )

    try:
        if notifications:
            db.add_all(notifications)

        db.commit()
    except Exception:
        db.rollback()
        raise

    created_count = len(notifications)
    target_count = len(target_users)

    return NotificationBroadcastResponse(
        message="Broadcast processed successfully",
        scope=payload.scope,
        target_count=target_count,
        notifications_created=created_count,
        skipped_by_preferences=target_count - created_count,
    )


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
