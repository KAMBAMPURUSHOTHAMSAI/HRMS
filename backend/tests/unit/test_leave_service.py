from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.models.leave_balance import LeaveBalance
from app.models.leave_type import LeaveType
from app.schemas.leave import LeaveDecision, LeaveRequestCreate
from app.services import leave_service


def create_leave_type(
    db,
    *,
    quota=Decimal("12.00"),
    is_paid=True,
    is_active=True,
    code="CASUAL",
):
    leave_type = LeaveType(
        code=code,
        name=f"{code.title()} Leave",
        description="Leave type for automated tests",
        is_paid=is_paid,
        annual_quota=quota,
        is_active=is_active,
    )
    db.add(leave_type)
    db.commit()
    db.refresh(leave_type)
    return leave_type


def make_leave_payload(
    leave_type_id,
    start_date=date(2026, 10, 19),
    end_date=date(2026, 10, 20),
    reason="Family personal work",
):
    return LeaveRequestCreate(
        leave_type_id=leave_type_id,
        start_date=start_date,
        end_date=end_date,
        reason=reason,
    )


def test_working_days_by_year_counts_weekdays_correctly():
    result = leave_service.working_days_by_year(
        date(2026, 12, 31),
        date(2027, 1, 4),
    )

    assert result == {
        2026: Decimal("1.00"),
        2027: Decimal("2.00"),
    }


def test_working_days_rejects_end_date_before_start_date():
    with pytest.raises(HTTPException) as error:
        leave_service.working_days_by_year(
            date(2026, 10, 20),
            date(2026, 10, 19),
        )

    assert error.value.status_code == 422
    assert error.value.detail == "End date cannot be before start date"


def test_working_days_rejects_weekend_only_period():
    with pytest.raises(HTTPException) as error:
        leave_service.working_days_by_year(
            date(2026, 10, 17),  # Saturday
            date(2026, 10, 18),  # Sunday
        )

    assert error.value.status_code == 422
    assert error.value.detail == (
        "The selected period contains no working days"
    )


def test_apply_leave_creates_pending_request_and_balance(
    db,
    make_employee,
):
    employee = make_employee()
    leave_type = create_leave_type(db)

    result = leave_service.apply_leave(
        db,
        employee.user,
        make_leave_payload(leave_type.id),
    )

    assert result.status == "PENDING"
    assert result.employee_id == employee.id
    assert result.leave_type_id == leave_type.id
    assert result.total_days == Decimal("2.00")
    assert result.reason == "Family personal work"

    balance = db.scalar(
        select(LeaveBalance).where(
            LeaveBalance.employee_id == employee.id,
            LeaveBalance.leave_type_id == leave_type.id,
            LeaveBalance.year == 2026,
        )
    )

    assert balance is not None
    assert balance.entitled_days == Decimal("12.00")
    assert balance.used_days == Decimal("0.00")


def test_apply_leave_rejects_inactive_leave_type(
    db,
    make_employee,
):
    employee = make_employee()
    leave_type = create_leave_type(db, is_active=False)

    with pytest.raises(HTTPException) as error:
        leave_service.apply_leave(
            db,
            employee.user,
            make_leave_payload(leave_type.id),
        )

    assert error.value.status_code == 404
    assert error.value.detail == "Active leave type not found"


def test_apply_leave_rejects_overlapping_pending_request(
    db,
    make_employee,
):
    employee = make_employee()
    leave_type = create_leave_type(db)

    leave_service.apply_leave(
        db,
        employee.user,
        make_leave_payload(leave_type.id),
    )

    with pytest.raises(HTTPException) as error:
        leave_service.apply_leave(
            db,
            employee.user,
            make_leave_payload(
                leave_type.id,
                start_date=date(2026, 10, 20),
                end_date=date(2026, 10, 21),
                reason="Overlapping leave request",
            ),
        )

    assert error.value.status_code == 409
    assert error.value.detail == (
        "This leave period overlaps with an existing request"
    )


def test_apply_leave_rejects_insufficient_balance(
    db,
    make_employee,
):
    employee = make_employee()
    leave_type = create_leave_type(
        db,
        quota=Decimal("1.00"),
    )

    with pytest.raises(HTTPException) as error:
        leave_service.apply_leave(
            db,
            employee.user,
            make_leave_payload(leave_type.id),
        )

    assert error.value.status_code == 409
    assert "Insufficient" in error.value.detail
    assert "Available: 1.00 days" in error.value.detail


def test_apply_leave_rejects_invalid_date_range(
    db,
    make_employee,
):
    employee = make_employee()
    leave_type = create_leave_type(db)

    with pytest.raises(HTTPException) as error:
        leave_service.apply_leave(
            db,
            employee.user,
            make_leave_payload(
                leave_type.id,
                start_date=date(2026, 10, 21),
                end_date=date(2026, 10, 19),
            ),
        )

    assert error.value.status_code == 422
    assert error.value.detail == "End date cannot be before start date"


def test_approve_leave_updates_used_balance(
    db,
    make_employee,
    admin_user,
):
    employee = make_employee()
    leave_type = create_leave_type(db)

    request = leave_service.apply_leave(
        db,
        employee.user,
        make_leave_payload(leave_type.id),
    )

    approved = leave_service.decide_leave_request(
        db,
        request.id,
        LeaveDecision(decision_note="Approved for testing"),
        admin_user,
        approve=True,
    )

    assert approved.status == "APPROVED"
    assert approved.approved_by_user_id == admin_user.id
    assert approved.decision_note == "Approved for testing"

    balance = db.scalar(
        select(LeaveBalance).where(
            LeaveBalance.employee_id == employee.id,
            LeaveBalance.leave_type_id == leave_type.id,
            LeaveBalance.year == 2026,
        )
    )

    assert balance.used_days == Decimal("2.00")
    assert balance.entitled_days - balance.used_days == Decimal("10.00")


def test_reject_leave_does_not_consume_balance(
    db,
    make_employee,
    admin_user,
):
    employee = make_employee()
    leave_type = create_leave_type(db)

    request = leave_service.apply_leave(
        db,
        employee.user,
        make_leave_payload(leave_type.id),
    )

    rejected = leave_service.decide_leave_request(
        db,
        request.id,
        LeaveDecision(decision_note="Insufficient staffing"),
        admin_user,
        approve=False,
    )

    assert rejected.status == "REJECTED"
    assert rejected.decision_note == "Insufficient staffing"

    balance = db.scalar(
        select(LeaveBalance).where(
            LeaveBalance.employee_id == employee.id,
            LeaveBalance.leave_type_id == leave_type.id,
            LeaveBalance.year == 2026,
        )
    )

    assert balance.used_days == Decimal("0.00")


def test_non_pending_leave_request_cannot_be_decided_again(
    db,
    make_employee,
    admin_user,
):
    employee = make_employee()
    leave_type = create_leave_type(db)

    request = leave_service.apply_leave(
        db,
        employee.user,
        make_leave_payload(leave_type.id),
    )

    leave_service.decide_leave_request(
        db,
        request.id,
        LeaveDecision(decision_note="Approved"),
        admin_user,
        approve=True,
    )

    with pytest.raises(HTTPException) as error:
        leave_service.decide_leave_request(
            db,
            request.id,
            LeaveDecision(decision_note="Trying again"),
            admin_user,
            approve=False,
        )

    assert error.value.status_code == 409
    assert error.value.detail == (
        "Only pending leave requests can be decided"
    )


def test_inactive_employee_cannot_apply_for_leave(
    db,
    make_employee,
):
    employee = make_employee(employment_status="INACTIVE")
    leave_type = create_leave_type(db)

    with pytest.raises(HTTPException) as error:
        leave_service.apply_leave(
            db,
            employee.user,
            make_leave_payload(leave_type.id),
        )

    assert error.value.status_code == 403
    assert error.value.detail == (
        "Inactive employees cannot apply for leave"
    )


def test_user_without_employee_profile_cannot_apply(
    db,
    make_user,
):
    user = make_user(email="no.leave.profile@example.com")
    leave_type = create_leave_type(db)

    with pytest.raises(HTTPException) as error:
        leave_service.apply_leave(
            db,
            user,
            make_leave_payload(leave_type.id),
        )

    assert error.value.status_code == 404
    assert error.value.detail == (
        "Employee profile is not configured for this account"
    )


def test_unpaid_leave_does_not_consume_paid_leave_balance(
    db,
    make_employee,
    admin_user,
):
    employee = make_employee()
    leave_type = create_leave_type(
        db,
        code="UNPAID",
        is_paid=False,
        quota=Decimal("0.00"),
    )

    request = leave_service.apply_leave(
        db,
        employee.user,
        make_leave_payload(leave_type.id),
    )

    approved = leave_service.decide_leave_request(
        db,
        request.id,
        LeaveDecision(decision_note="Unpaid leave approved"),
        admin_user,
        approve=True,
    )

    assert approved.status == "APPROVED"

    balance = db.scalar(
        select(LeaveBalance).where(
            LeaveBalance.employee_id == employee.id,
            LeaveBalance.leave_type_id == leave_type.id,
            LeaveBalance.year == 2026,
        )
    )

    # The service only creates balances for paid leave types.
    assert balance is None