from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

import app.api.v1.endpoints.leaves as leave_endpoints

from app.models.leave_balance import LeaveBalance
from app.models.leave_type import LeaveType


@pytest.fixture
def leave_type(db):
    item = LeaveType(
        code="CASUAL",
        name="Casual Leave",
        description="Casual leave used in API tests",
        is_paid=True,
        annual_quota=Decimal("12.00"),
        is_active=True,
    )

    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@pytest.fixture(autouse=True)
def disable_leave_notifications(monkeypatch):
    """
    Keep API tests focused on leave behavior.
    Notification and email workflows can be tested separately.
    """

    monkeypatch.setattr(
        leave_endpoints,
        "_notify_leave_application",
        lambda *args, **kwargs: None,
    )

    monkeypatch.setattr(
        leave_endpoints,
        "_notify_leave_decision",
        lambda *args, **kwargs: None,
    )


def leave_payload(
    leave_type_id,
    start_date="2026-10-19",
    end_date="2026-10-20",
    reason="Family personal work",
):
    return {
        "leave_type_id": leave_type_id,
        "start_date": start_date,
        "end_date": end_date,
        "reason": reason,
    }


def apply_leave(
    client,
    headers,
    leave_type,
    *,
    start_date="2026-10-19",
    end_date="2026-10-20",
    reason="Family personal work",
):
    return client.post(
        "/api/v1/leaves",
        headers=headers,
        json=leave_payload(
            leave_type.id,
            start_date,
            end_date,
            reason,
        ),
    )


def test_apply_leave_requires_authentication(
    client,
    leave_type,
):
    response = client.post(
        "/api/v1/leaves",
        json=leave_payload(leave_type.id),
    )

    assert response.status_code == 401


def test_employee_can_apply_for_leave(
    client,
    employee_user,
    employee_headers,
    make_employee,
    leave_type,
):
    employee = make_employee(user=employee_user)

    response = apply_leave(
        client,
        employee_headers,
        leave_type,
    )

    assert response.status_code == 201

    data = response.json()
    assert data["employee_id"] == employee.id
    assert data["leave_type_id"] == leave_type.id
    assert data["status"] == "PENDING"
    assert data["total_days"] == "2.00"
    assert data["reason"] == "Family personal work"


def test_employee_can_view_own_leave_history(
    client,
    employee_user,
    employee_headers,
    make_employee,
    leave_type,
):
    make_employee(user=employee_user)

    create_response = apply_leave(
        client,
        employee_headers,
        leave_type,
    )
    assert create_response.status_code == 201

    response = client.get(
        "/api/v1/leaves/me",
        headers=employee_headers,
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["status"] == "PENDING"


def test_employee_can_view_leave_balances(
    client,
    employee_user,
    employee_headers,
    make_employee,
    leave_type,
):
    make_employee(user=employee_user)

    response = client.get(
        "/api/v1/leaves/me/balances",
        params={"year": 2026},
        headers=employee_headers,
    )

    assert response.status_code == 200

    balances = response.json()
    matching = [
        item
        for item in balances
        if item["leave_type_id"] == leave_type.id
    ]

    assert len(matching) == 1
    assert matching[0]["entitled_days"] == "12.00"
    assert matching[0]["used_days"] == "0.00"
    assert matching[0]["available_days"] == "12.00"


def test_overlapping_leave_application_returns_conflict(
    client,
    employee_user,
    employee_headers,
    make_employee,
    leave_type,
):
    make_employee(user=employee_user)

    first = apply_leave(
        client,
        employee_headers,
        leave_type,
    )
    assert first.status_code == 201

    second = apply_leave(
        client,
        employee_headers,
        leave_type,
        start_date="2026-10-20",
        end_date="2026-10-21",
        reason="Overlapping request",
    )

    assert second.status_code == 409
    assert second.json()["detail"] == (
        "This leave period overlaps with an existing request"
    )


def test_invalid_leave_date_range_returns_422(
    client,
    employee_user,
    employee_headers,
    make_employee,
    leave_type,
):
    make_employee(user=employee_user)

    response = apply_leave(
        client,
        employee_headers,
        leave_type,
        start_date="2026-10-21",
        end_date="2026-10-19",
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "End date cannot be before start date"
    )


def test_weekend_only_leave_returns_422(
    client,
    employee_user,
    employee_headers,
    make_employee,
    leave_type,
):
    make_employee(user=employee_user)

    response = apply_leave(
        client,
        employee_headers,
        leave_type,
        start_date="2026-10-17",
        end_date="2026-10-18",
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "The selected period contains no working days"
    )


def test_employee_cannot_view_all_leave_requests(
    client,
    employee_headers,
):
    response = client.get(
        "/api/v1/leaves",
        headers=employee_headers,
    )

    assert response.status_code == 403


def test_admin_can_approve_leave_and_balance_is_updated(
    client,
    db,
    employee_user,
    employee_headers,
    admin_headers,
    make_employee,
    leave_type,
):
    employee = make_employee(user=employee_user)

    application = apply_leave(
        client,
        employee_headers,
        leave_type,
    )
    assert application.status_code == 201

    request_id = application.json()["id"]

    response = client.post(
        f"/api/v1/leaves/{request_id}/approve",
        headers=admin_headers,
        json={"decision_note": "Approved for testing"},
    )

    assert response.status_code == 200

    data = response.json()
    assert data["id"] == request_id
    assert data["status"] == "APPROVED"
    assert data["decision_note"] == "Approved for testing"

    balance = db.scalar(
        select(LeaveBalance).where(
            LeaveBalance.employee_id == employee.id,
            LeaveBalance.leave_type_id == leave_type.id,
            LeaveBalance.year == 2026,
        )
    )

    assert balance is not None
    assert balance.used_days == Decimal("2.00")


def test_admin_can_reject_leave(
    client,
    employee_user,
    employee_headers,
    admin_headers,
    make_employee,
    leave_type,
):
    make_employee(user=employee_user)

    application = apply_leave(
        client,
        employee_headers,
        leave_type,
    )
    assert application.status_code == 201

    request_id = application.json()["id"]

    response = client.post(
        f"/api/v1/leaves/{request_id}/reject",
        headers=admin_headers,
        json={"decision_note": "Please choose other dates"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "REJECTED"
    assert response.json()["decision_note"] == (
        "Please choose other dates"
    )


def test_employee_cannot_approve_leave(
    client,
    employee_user,
    employee_headers,
    make_employee,
    leave_type,
):
    make_employee(user=employee_user)

    application = apply_leave(
        client,
        employee_headers,
        leave_type,
    )
    assert application.status_code == 201

    request_id = application.json()["id"]

    response = client.post(
        f"/api/v1/leaves/{request_id}/approve",
        headers=employee_headers,
        json={"decision_note": "Self approval attempt"},
    )

    assert response.status_code == 403


def test_unauthenticated_user_cannot_view_leave_history(client):
    response = client.get("/api/v1/leaves/me")

    assert response.status_code == 401