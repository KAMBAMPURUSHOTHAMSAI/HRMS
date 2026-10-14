from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi import HTTPException

import app.services.attendance_service as attendance_service
from app.models.attendance import Attendance


# Naive datetimes are used in these service tests because SQLite
# does not preserve timezone information in DateTime columns.
TEST_NOW = datetime(2026, 10, 13, 9, 0, 0)


def test_check_in_creates_present_record(
    db,
    make_employee,
    monkeypatch,
):
    employee = make_employee()

    monkeypatch.setattr(
        attendance_service,
        "company_now",
        lambda: TEST_NOW,
    )

    record = attendance_service.check_in(db, employee.user)

    assert record.employee_id == employee.id
    assert record.attendance_date == TEST_NOW.date()
    assert record.check_in == TEST_NOW
    assert record.status == "PRESENT"
    assert record.check_out is None


def test_duplicate_check_in_returns_conflict(
    db,
    make_employee,
    monkeypatch,
):
    employee = make_employee()

    monkeypatch.setattr(
        attendance_service,
        "company_now",
        lambda: TEST_NOW,
    )

    attendance_service.check_in(db, employee.user)

    with pytest.raises(HTTPException) as error:
        attendance_service.check_in(db, employee.user)

    assert error.value.status_code == 409
    assert error.value.detail == (
        "Attendance has already been recorded for today"
    )


def test_check_out_calculates_working_minutes(
    db,
    make_employee,
    monkeypatch,
):
    employee = make_employee()

    moments = iter(
        [
            TEST_NOW,
            TEST_NOW + timedelta(minutes=75),
        ]
    )

    monkeypatch.setattr(
        attendance_service,
        "company_now",
        lambda: next(moments),
    )

    attendance_service.check_in(db, employee.user)
    record = attendance_service.check_out(db, employee.user)

    assert record.check_out == TEST_NOW + timedelta(minutes=75)
    assert record.working_minutes == 75


def test_check_out_without_check_in_returns_not_found(
    db,
    make_employee,
    monkeypatch,
):
    employee = make_employee()

    monkeypatch.setattr(
        attendance_service,
        "company_now",
        lambda: TEST_NOW,
    )

    with pytest.raises(HTTPException) as error:
        attendance_service.check_out(db, employee.user)

    assert error.value.status_code == 404
    assert error.value.detail == "Check in before checking out"


def test_second_check_out_returns_conflict(
    db,
    make_employee,
    monkeypatch,
):
    employee = make_employee()

    moments = iter(
        [
            TEST_NOW,
            TEST_NOW + timedelta(minutes=60),
            TEST_NOW + timedelta(minutes=90),
        ]
    )

    monkeypatch.setattr(
        attendance_service,
        "company_now",
        lambda: next(moments),
    )

    attendance_service.check_in(db, employee.user)
    attendance_service.check_out(db, employee.user)

    with pytest.raises(HTTPException) as error:
        attendance_service.check_out(db, employee.user)

    assert error.value.status_code == 409
    assert error.value.detail == (
        "Attendance has already been checked out"
    )


def test_check_out_before_check_in_time_is_rejected(
    db,
    make_employee,
    monkeypatch,
):
    employee = make_employee()

    monkeypatch.setattr(
        attendance_service,
        "company_now",
        lambda: TEST_NOW,
    )

    attendance_service.check_in(db, employee.user)

    monkeypatch.setattr(
        attendance_service,
        "company_now",
        lambda: TEST_NOW - timedelta(minutes=1),
    )

    with pytest.raises(HTTPException) as error:
        attendance_service.check_out(db, employee.user)

    assert error.value.status_code == 422
    assert error.value.detail == (
        "Check-out time must be after check-in time"
    )


def test_monthly_summary_calculates_total_hours(
    db,
    make_employee,
):
    employee = make_employee()

    db.add_all(
        [
            Attendance(
                employee_id=employee.id,
                attendance_date=date(2026, 9, 1),
                check_in=datetime(2026, 9, 1, 9, 0),
                check_out=datetime(2026, 9, 1, 14, 0),
                working_minutes=300,
                status="PRESENT",
            ),
            Attendance(
                employee_id=employee.id,
                attendance_date=date(2026, 9, 2),
                check_in=datetime(2026, 9, 2, 9, 0),
                check_out=datetime(2026, 9, 2, 10, 30),
                working_minutes=90,
                status="PRESENT",
            ),
        ]
    )
    db.commit()

    summary = attendance_service.get_my_monthly_summary(
        db,
        employee.user,
        2026,
        9,
    )

    assert summary.year == 2026
    assert summary.month == 9
    assert summary.days_recorded == 2
    assert summary.total_worked_minutes == 390
    assert summary.total_worked_hours == Decimal("6.50")


def test_my_attendance_rejects_invalid_date_range(
    db,
    make_employee,
):
    employee = make_employee()

    with pytest.raises(HTTPException) as error:
        attendance_service.get_my_attendance(
            db,
            employee.user,
            start_date=date(2026, 10, 20),
            end_date=date(2026, 10, 10),
        )

    assert error.value.status_code == 422
    assert error.value.detail == (
        "start_date cannot be after end_date"
    )


def test_inactive_employee_cannot_check_in(
    db,
    make_employee,
    monkeypatch,
):
    employee = make_employee(employment_status="INACTIVE")

    monkeypatch.setattr(
        attendance_service,
        "company_now",
        lambda: TEST_NOW,
    )

    with pytest.raises(HTTPException) as error:
        attendance_service.check_in(db, employee.user)

    assert error.value.status_code == 403
    assert error.value.detail == (
        "Inactive employees cannot record attendance"
    )


def test_employee_without_profile_cannot_check_in(
    db,
    make_user,
    monkeypatch,
):
    user = make_user(
        email="no.profile@example.com",
        role_name="EMPLOYEE",
    )

    monkeypatch.setattr(
        attendance_service,
        "company_now",
        lambda: TEST_NOW,
    )

    with pytest.raises(HTTPException) as error:
        attendance_service.check_in(db, user)

    assert error.value.status_code == 404
    assert error.value.detail == (
        "Employee profile is not configured for this account"
    )