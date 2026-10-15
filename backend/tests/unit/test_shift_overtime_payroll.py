from datetime import date, datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from app.models.attendance import Attendance
from app.models.payroll_component_line import PayrollComponentLine
from app.models.shift import Shift
from app.models.shift_assignment import ShiftAssignment
from app.services import payroll_service


PAYROLL_YEAR = 2026
PAYROLL_MONTH = 9
PAYROLL_TODAY = date(2026, 10, 13)
COMPANY_TZ = ZoneInfo("Asia/Kolkata")


@pytest.fixture(autouse=True)
def freeze_payroll_clock(monkeypatch):
    """Keep this overtime payroll test deterministic."""
    monkeypatch.setattr(payroll_service, "company_today", lambda: PAYROLL_TODAY)
    monkeypatch.setattr(
        payroll_service,
        "now_local",
        lambda: datetime(2026, 10, 13, 12, 0, tzinfo=COMPANY_TZ),
    )


def test_shift_overtime_is_added_to_payroll_gross_and_component_snapshot(
    db,
    admin_user,
    make_employee,
):
    # Legacy monthly salary becomes the employee's Basic Pay (as in existing tests).
    employee = make_employee(
        monthly_salary=Decimal("50000.00"),
        joining_date=date(2024, 1, 1),
    )

    shift = Shift(
        name="OT Payroll Test Shift",
        shift_type="GENERAL",
        start_time=time(9, 0),
        end_time=time(18, 0),
        break_minutes=60,
        grace_minutes=10,
        expected_work_minutes=480,
        overtime_multiplier=Decimal("1.50"),
        is_active=True,
        created_by_user_id=admin_user.id,
    )
    db.add(shift)
    db.flush()

    db.add(
        ShiftAssignment(
            shift_id=shift.id,
            employee_id=employee.id,
            department_id=None,
            effective_from=date(2026, 9, 1),
            effective_to=None,
            assigned_by_user_id=admin_user.id,
        )
    )

    overtime_date = date(2026, 9, 2)  # Wednesday in the September 2026 payroll period.
    db.add(
        Attendance(
            employee_id=employee.id,
            attendance_date=overtime_date,
            check_in=datetime.combine(overtime_date, time(9, 0)),
            check_out=datetime.combine(overtime_date, time(20, 0)),
            # Elapsed duration: 11 hours. Less 60 min break and 480 min expected work
            # gives 120 overtime minutes, matching the shift-report formula.
            working_minutes=660,
            status="PRESENT",
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
    assert len(run.records) == 1
    record = run.records[0]
    assert record.employee_id == employee.id

    overtime_lines = db.scalars(
        select(PayrollComponentLine).where(
            PayrollComponentLine.payroll_record_id == record.id,
            PayrollComponentLine.component_code == "SHIFT_OVERTIME",
        )
    ).all()
    assert len(overtime_lines) == 1

    overtime_line = overtime_lines[0]
    # Basic Pay 50,000 / 22 working days; 120 overtime minutes at 1.5x
    # against 480 expected minutes = 852.27.
    assert overtime_line.amount == Decimal("852.27")
    assert overtime_line.component_type == "EARNING"
    assert overtime_line.is_taxable is True
    assert "2.00 hours" in overtime_line.calculation_details
    assert "120 min at 1.50x" in overtime_line.calculation_details

    assert record.base_pay == Decimal("50000.00")
    assert record.other_earnings == Decimal("852.27")
    assert record.gross_salary == Decimal("50852.27")
    assert record.net_salary == record.gross_salary - record.lop_deduction - record.other_deductions
