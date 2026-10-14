from datetime import date, datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.models.attendance import Attendance
from app.models.leave_request import LeaveRequest
from app.models.leave_type import LeaveType
from app.models.payroll_adjustment import PayrollAdjustment
from app.models.payroll_record import PayrollRecord
from app.services import payroll_service
from app.schemas.payroll import PayrollAdjustmentCreate


PAYROLL_YEAR = 2026
PAYROLL_MONTH = 9
PAYROLL_TODAY = date(2026, 10, 13)
COMPANY_TZ = ZoneInfo("Asia/Kolkata")


@pytest.fixture(autouse=True)
def freeze_payroll_clock(monkeypatch):
    """Keep the payroll-period tests deterministic."""

    monkeypatch.setattr(
        payroll_service,
        "company_today",
        lambda: PAYROLL_TODAY,
    )
    monkeypatch.setattr(
        payroll_service,
        "now_local",
        lambda: datetime(2026, 10, 13, 12, 0, tzinfo=COMPANY_TZ),
    )


def generate_test_run(db, admin_user, make_employee):
    """Generate September 2026 payroll for one test employee."""

    make_employee()

    return payroll_service.generate_payroll_run(
        db,
        PAYROLL_YEAR,
        PAYROLL_MONTH,
        admin_user,
    )


def test_generate_payroll_calculates_attendance_paid_leave_and_lop(
    db,
    admin_user,
    make_employee,
):
    employee = make_employee(
        monthly_salary=Decimal("50000.00"),
        joining_date=date(2024, 1, 1),
    )

    # Ten completed working days.
    attendance_dates = [
        date(2026, 9, day)
        for day in [1, 2, 3, 4, 7, 8, 9, 10, 11, 16]
    ]

    for attendance_date in attendance_dates:
        db.add(
            Attendance(
                employee_id=employee.id,
                attendance_date=attendance_date,
                check_in=datetime.combine(
                    attendance_date,
                    time(9, 0),
                ),
                check_out=datetime.combine(
                    attendance_date,
                    time(17, 0),
                ),
                working_minutes=480,
                status="PRESENT",
            )
        )

    paid_leave_type = LeaveType(
        code="CASUAL",
        name="Casual Leave",
        description="Paid leave for payroll testing",
        is_paid=True,
        annual_quota=Decimal("12.00"),
        is_active=True,
    )
    db.add(paid_leave_type)
    db.flush()

    # September 14 and 15 are two working days.
    db.add(
        LeaveRequest(
            employee_id=employee.id,
            leave_type_id=paid_leave_type.id,
            start_date=date(2026, 9, 14),
            end_date=date(2026, 9, 15),
            total_days=Decimal("2.00"),
            reason="Approved paid leave",
            status="APPROVED",
        )
    )
    db.commit()

    run = payroll_service.generate_payroll_run(
        db,
        PAYROLL_YEAR,
        PAYROLL_MONTH,
        admin_user,
    )

    assert run.status == "GENERATED"
    assert run.year == PAYROLL_YEAR
    assert run.month == PAYROLL_MONTH
    assert len(run.records) == 1

    record = run.records[0]

    assert record.employee_id == employee.id
    assert record.eligible_working_days == 22
    assert record.present_days == Decimal("10.00")
    assert record.paid_leave_days == Decimal("2.00")
    assert record.payable_days == Decimal("12.00")
    assert record.lop_days == Decimal("10.00")

    assert record.base_pay == Decimal("50000.00")
    assert record.lop_deduction == Decimal("22727.27")
    assert record.gross_salary == Decimal("50000.00")
    assert record.net_salary == Decimal("27272.73")
    assert record.credit_status == "PENDING"


def test_payroll_cannot_be_generated_for_current_month(
    db,
    admin_user,
):
    with pytest.raises(HTTPException) as error:
        payroll_service.generate_payroll_run(
            db,
            2026,
            10,
            admin_user,
        )

    assert error.value.status_code == 422
    assert error.value.detail == (
        "Payroll can only be generated for a completed month"
    )


def test_duplicate_monthly_payroll_is_rejected(
    db,
    admin_user,
    make_employee,
):
    generate_test_run(db, admin_user, make_employee)

    with pytest.raises(HTTPException) as error:
        payroll_service.generate_payroll_run(
            db,
            PAYROLL_YEAR,
            PAYROLL_MONTH,
            admin_user,
        )

    assert error.value.status_code == 409
    assert error.value.detail == (
        "Payroll has already been generated for this month"
    )


def test_payroll_generation_requires_eligible_employees(
    db,
    admin_user,
):
    with pytest.raises(HTTPException) as error:
        payroll_service.generate_payroll_run(
            db,
            PAYROLL_YEAR,
            PAYROLL_MONTH,
            admin_user,
        )

    assert error.value.status_code == 409
    assert error.value.detail == (
        "No eligible active employees exist for this payroll period"
    )


def test_adjustments_recalculate_gross_and_net_salary(
    db,
    admin_user,
    make_employee,
):
    employee = make_employee(
        monthly_salary=Decimal("50000.00"),
    )

    run = payroll_service.generate_payroll_run(
        db,
        PAYROLL_YEAR,
        PAYROLL_MONTH,
        admin_user,
    )
    record = run.records[0]

    # No attendance means the generated record initially has zero net pay.
    assert record.net_salary == Decimal("0.00")

    earning = payroll_service.add_payroll_adjustment(
        db,
        run.id,
        PayrollAdjustmentCreate(
            employee_id=employee.id,
            adjustment_type="EARNING",
            amount=Decimal("1000.00"),
            description="Performance bonus",
        ),
        admin_user,
    )

    assert earning.adjustment_type == "EARNING"
    assert earning.amount == Decimal("1000.00")

    db.refresh(record)
    assert record.other_earnings == Decimal("1000.00")
    assert record.gross_salary == Decimal("51000.00")
    assert record.net_salary == Decimal("1000.00")

    deduction = payroll_service.add_payroll_adjustment(
        db,
        run.id,
        PayrollAdjustmentCreate(
            employee_id=employee.id,
            adjustment_type="DEDUCTION",
            amount=Decimal("250.00"),
            description="Other payroll deduction",
        ),
        admin_user,
    )

    assert deduction.adjustment_type == "DEDUCTION"

    db.refresh(record)
    assert record.other_earnings == Decimal("1000.00")
    assert record.other_deductions == Decimal("250.00")
    assert record.gross_salary == Decimal("51000.00")
    assert record.net_salary == Decimal("750.00")

    adjustments = db.scalars(
        select(PayrollAdjustment).where(
            PayrollAdjustment.payroll_record_id == record.id
        )
    ).all()

    assert len(adjustments) == 2


def test_adjustment_cannot_make_net_salary_negative(
    db,
    admin_user,
    make_employee,
):
    employee = make_employee()

    run = payroll_service.generate_payroll_run(
        db,
        PAYROLL_YEAR,
        PAYROLL_MONTH,
        admin_user,
    )

    with pytest.raises(HTTPException) as error:
        payroll_service.add_payroll_adjustment(
            db,
            run.id,
            PayrollAdjustmentCreate(
                employee_id=employee.id,
                adjustment_type="DEDUCTION",
                amount=Decimal("1.00"),
                description="Test negative net rejection",
            ),
            admin_user,
        )

    assert error.value.status_code == 422
    assert error.value.detail == (
        "Adjustments cannot make net salary negative"
    )

    # The failed adjustment must not remain in the database.
    count = db.scalar(
        select(PayrollAdjustment.id).where(
            PayrollAdjustment.payroll_record_id
            == run.records[0].id
        )
    )
    assert count is None


def test_locked_payroll_rejects_adjustments(
    db,
    admin_user,
    make_employee,
):
    employee = make_employee()

    run = payroll_service.generate_payroll_run(
        db,
        PAYROLL_YEAR,
        PAYROLL_MONTH,
        admin_user,
    )

    locked_run = payroll_service.lock_payroll(
        db,
        run.id,
        admin_user,
    )

    assert locked_run.status == "LOCKED"
    assert locked_run.locked_by_user_id == admin_user.id
    assert locked_run.locked_at is not None

    with pytest.raises(HTTPException) as error:
        payroll_service.add_payroll_adjustment(
            db,
            run.id,
            PayrollAdjustmentCreate(
                employee_id=employee.id,
                adjustment_type="EARNING",
                amount=Decimal("500.00"),
                description="Adjustment after lock",
            ),
            admin_user,
        )

    assert error.value.status_code == 409
    assert error.value.detail == (
        "Payroll adjustments are not allowed after locking"
    )


def test_already_locked_payroll_cannot_be_locked_again(
    db,
    admin_user,
    make_employee,
):
    run = generate_test_run(db, admin_user, make_employee)

    payroll_service.lock_payroll(db, run.id, admin_user)

    with pytest.raises(HTTPException) as error:
        payroll_service.lock_payroll(
            db,
            run.id,
            admin_user,
        )

    assert error.value.status_code == 409
    assert error.value.detail == "Payroll run is already locked"


def test_salary_credit_requires_locked_payroll(
    db,
    admin_user,
    make_employee,
):
    run = generate_test_run(db, admin_user, make_employee)

    with pytest.raises(HTTPException) as error:
        payroll_service.simulate_salary_credit(db, run.id)

    assert error.value.status_code == 409
    assert error.value.detail == (
        "Lock the payroll run before simulating salary credit"
    )


def test_salary_credit_can_be_simulated_only_once(
    db,
    admin_user,
    make_employee,
):
    run = generate_test_run(db, admin_user, make_employee)
    payroll_service.lock_payroll(db, run.id, admin_user)

    credited_run = payroll_service.simulate_salary_credit(
        db,
        run.id,
    )

    record = credited_run.records[0]
    assert record.credit_status == "SIMULATED"
    assert record.simulated_credit_at is not None

    with pytest.raises(HTTPException) as error:
        payroll_service.simulate_salary_credit(
            db,
            run.id,
        )

    assert error.value.status_code == 409
    assert error.value.detail == (
        "Salary credit was already simulated"
    )


def test_missing_payroll_run_returns_not_found(db):
    with pytest.raises(HTTPException) as error:
        payroll_service.get_payroll_run(db, 99999)

    assert error.value.status_code == 404
    assert error.value.detail == "Payroll run not found"