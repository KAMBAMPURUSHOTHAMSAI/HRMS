
from datetime import datetime, timezone

import pytest

from app.models.email_log import EmailDeliveryLog
from app.models.notification import Notification
from app.services import notification_service


BASE_URL = "/api/v1/notifications"


def create_notification(
    db,
    user_id: int,
    *,
    title: str = "Test notification",
    is_read: bool = False,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        event_type="TEST_EVENT",
        title=title,
        message="Notification created for API testing.",
        is_read=is_read,
        read_at=datetime.now(timezone.utc) if is_read else None,
        extra_data={},
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def create_email_log(
    db,
    user_id: int | None,
    *,
    status: str = "FAILED",
) -> EmailDeliveryLog:
    log = EmailDeliveryLog(
        user_id=user_id,
        recipient_email="test@example.com",
        event_type="TEST_EVENT",
        subject="HRMS test email",
        template_name="test_template",
        email_context={},
        status=status,
        attempt_count=1,
        error_message="Simulated delivery failure"
        if status == "FAILED"
        else None,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def test_employee_can_list_own_notifications(
    client, db, employee_user, admin_user, employee_headers
):
    own_notification = create_notification(
        db, employee_user.id, title="My notification"
    )
    other_notification = create_notification(
        db, admin_user.id, title="Other user's notification"
    )

    response = client.get(
        f"{BASE_URL}/me",
        headers=employee_headers,
    )

    assert response.status_code == 200

    data = response.json()
    returned_ids = {item["id"] for item in data}

    assert own_notification.id in returned_ids
    assert other_notification.id not in returned_ids


def test_employee_can_filter_unread_notifications(
    client, db, employee_user, employee_headers
):
    unread = create_notification(
        db, employee_user.id, title="Unread notification"
    )
    create_notification(
        db,
        employee_user.id,
        title="Already read notification",
        is_read=True,
    )

    response = client.get(
        f"{BASE_URL}/me",
        params={"unread_only": "true"},
        headers=employee_headers,
    )

    assert response.status_code == 200

    data = response.json()
    returned_ids = {item["id"] for item in data}

    assert unread.id in returned_ids
    assert len(data) == 1
    assert all(item["is_read"] is False for item in data)


def test_employee_can_get_unread_notification_count(
    client, db, employee_user, admin_user, employee_headers
):
    create_notification(db, employee_user.id)
    create_notification(db, employee_user.id, title="Second unread")
    create_notification(
        db, employee_user.id, title="Read notification", is_read=True
    )
    create_notification(db, admin_user.id, title="Another user's notification")

    response = client.get(
        f"{BASE_URL}/me/unread-count",
        headers=employee_headers,
    )

    assert response.status_code == 200
    assert response.json()["unread_count"] == 2


def test_employee_can_mark_own_notification_as_read(
    client, db, employee_user, employee_headers
):
    notification = create_notification(db, employee_user.id)

    response = client.patch(
        f"{BASE_URL}/{notification.id}/read",
        headers=employee_headers,
    )

    assert response.status_code == 200

    db.refresh(notification)
    assert notification.is_read is True
    assert notification.read_at is not None


def test_employee_cannot_mark_another_users_notification_as_read(
    client, db, admin_user, employee_headers
):
    notification = create_notification(db, admin_user.id)

    response = client.patch(
        f"{BASE_URL}/{notification.id}/read",
        headers=employee_headers,
    )

    assert response.status_code == 404


def test_employee_can_mark_all_own_notifications_as_read(
    client, db, employee_user, admin_user, employee_headers
):
    first = create_notification(db, employee_user.id, title="First unread")
    second = create_notification(db, employee_user.id, title="Second unread")
    already_read = create_notification(
        db, employee_user.id, title="Already read", is_read=True
    )
    another_user_notification = create_notification(db, admin_user.id)

    response = client.post(
        f"{BASE_URL}/me/read-all",
        headers=employee_headers,
    )

    assert response.status_code == 200
    assert response.json()["updated_count"] == 2

    db.refresh(first)
    db.refresh(second)
    db.refresh(already_read)
    db.refresh(another_user_notification)

    assert first.is_read is True
    assert second.is_read is True
    assert already_read.is_read is True
    assert another_user_notification.is_read is False


def test_admin_can_list_email_logs_by_status(
    client, db, admin_user, admin_headers
):
    failed_log = create_email_log(db, admin_user.id, status="FAILED")
    create_email_log(db, admin_user.id, status="SENT")

    response = client.get(
        f"{BASE_URL}/admin/email-logs",
        params={"status_filter": "FAILED"},
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == failed_log.id
    assert data[0]["status"] == "FAILED"


def test_employee_cannot_access_admin_email_logs(
    client, employee_headers
):
    response = client.get(
        f"{BASE_URL}/admin/email-logs",
        headers=employee_headers,
    )

    assert response.status_code == 403


def test_email_log_list_rejects_invalid_status(
    client, admin_headers
):
    response = client.get(
        f"{BASE_URL}/admin/email-logs",
        params={"status_filter": "UNKNOWN"},
        headers=admin_headers,
    )

    assert response.status_code == 422


@pytest.mark.parametrize("initial_status", ["FAILED", "SKIPPED"])
def test_admin_can_retry_failed_or_skipped_email(
    client,
    db,
    admin_user,
    admin_headers,
    monkeypatch,
    initial_status,
):
    # Do not send a real email during an automated test.
    monkeypatch.setattr(
        notification_service,
        "deliver_email_log",
        lambda email_log_id: None,
    )

    log = create_email_log(
        db, admin_user.id, status=initial_status
    )

    response = client.post(
        f"{BASE_URL}/admin/email-logs/{log.id}/retry",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "PENDING"

    db.refresh(log)
    assert log.status == "PENDING"
    assert log.error_message is None


@pytest.mark.parametrize("initial_status", ["PENDING", "SENT"])
def test_admin_cannot_retry_pending_or_sent_email(
    client, db, admin_user, admin_headers, initial_status
):
    log = create_email_log(
        db, admin_user.id, status=initial_status
    )

    response = client.post(
        f"{BASE_URL}/admin/email-logs/{log.id}/retry",
        headers=admin_headers,
    )

    assert response.status_code == 409

    db.refresh(log)
    assert log.status == initial_status


def test_retry_returns_404_for_missing_email_log(
    client, admin_headers
):
    response = client.post(
        f"{BASE_URL}/admin/email-logs/999999/retry",
        headers=admin_headers,
    )

    assert response.status_code == 404
