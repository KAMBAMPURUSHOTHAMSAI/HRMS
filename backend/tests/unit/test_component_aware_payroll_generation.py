
from datetime import date, datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from app.models.attendance import Attendance
from app.models.employee_salary_component import EmployeeSalaryComponent
from app.models.payroll_component_line import PayrollComponentLine
from app.models.salary_component import SalaryComponent
from app.services import payroll_service
from app.schemas.payroll import PayrollAdjustmentCreate


PAYROLL_YEAR = 2026
PAYROLL_MONTH = 9
PAYROLL_TODAY = date(2026, 10, 13)
COMPANY_TZ = ZoneInfo("Asia/Kolkata")


@pytest.fixture(autouse=True)
def freeze_payroll_clock(monkeypatch):
    monkeypatch.setattr(
        payroll_service,
        "company_today",
        lambda: PAYROLL_TODAY,
    )
    monkeypatch.setattr(
        payroll_service,
        "now_local",
        lambda: datetime(
            2026, 10, 13, 12, 0, tzinfo=COMPANY_TZ
        ),
    )


def assign_basic_pay(db, employee, amount="25000.00"):
    component = SalaryComponent(
        code="BASIC_PAY",
        name="Basic Pay",
        description="Test basic pay component",
        component_type="EARNING",
        calculation_type="FIXED",
        default_amount=Decimal("0.00"),
        percentage_base="BASE_PAY",
        is_variable=False,
        is_taxable=True,
        is_active=True,
        created_by_user_id=None,
    )

    db.add(component)
    db.flush()

    assignment = EmployeeSalaryComponent(
        employee_id=employee.id,
        component_id=component.id,
        amount_override=Decimal(amount),
        effective_from=date(2026, 9, 1),
        effective_to=None,
        notes="Payroll integration test",
        assigned_by_user_id=None,
    )

    db.add(assignment)
    db.flush()

    return component


def add_full_attendance(db, employee):
    for day in payroll_service.iter_workdays(
        date(2026, 9, 1),
        date(2026, 9, 30),
    ):
        db.add(
            Attendance(
                employee_id=employee.id,
                attendance_date=day,
                check_in=datetime.combine(day, time(9, 0)),
                check_out=datetime.combine(day, time(17, 0)),
                working_minutes=480,
                status="PRESENT",
            )
        )

    db.flush()


def test_configured_basic_pay_flows_into_payroll_and_snapshot(
    db,
    admin_user,
    make_employee,
):
    employee = make_employee(
        monthly_salary=Decimal("50000.00"),
    )

    assign_basic_pay(db, employee)
    add_full_attendance(db, employee)
    db.commit()

    run = payroll_service.generate_payroll_run(
        db,
        PAYROLL_YEAR,
        PAYROLL_MONTH,
        admin_user,
    )

    record = next(
        item
        for item in run.records
        if item.employee_id == employee.id
    )

    assert record.eligible_working_days == 22
    assert record.present_days == Decimal("22.00")
    assert record.lop_days == Decimal("0.00")

    assert record.base_pay == Decimal("25000.00")
    assert record.lop_deduction == Decimal("0.00")
    assert record.gross_salary == Decimal("25000.00")
    assert record.net_salary == Decimal("25000.00")

    lines = list(
        db.scalars(
            select(PayrollComponentLine).where(
                PayrollComponentLine.payroll_record_id == record.id
            )
        ).all()
    )

    basic_lines = [
        line
        for line in lines
        if line.component_code == "BASIC_PAY"
    ]

    assert len(basic_lines) == 1
    assert basic_lines[0].amount == Decimal("25000.00")
    assert basic_lines[0].component_type == "EARNING"


def test_configured_basic_pay_applies_lop_deduction(
    db,
    admin_user,
    make_employee,
):
    employee = make_employee(
        monthly_salary=Decimal("50000.00"),
    )

    assign_basic_pay(db, employee)
    db.commit()

    run = payroll_service.generate_payroll_run(
        db,
        PAYROLL_YEAR,
        PAYROLL_MONTH,
        admin_user,
    )

    record = next(
        item
        for item in run.records
        if item.employee_id == employee.id
    )

    assert record.base_pay == Decimal("25000.00")
    assert record.lop_days == Decimal("22.00")
    assert record.lop_deduction == Decimal("25000.00")
    assert record.gross_salary == Decimal("25000.00")
    assert record.net_salary == Decimal("0.00")

    lines = list(
        db.scalars(
            select(PayrollComponentLine).where(
                PayrollComponentLine.payroll_record_id == record.id
            )
        ).all()
    )

    basic_line = next(
        line for line in lines
        if line.component_code == "BASIC_PAY"
    )
    lop_line = next(
        line for line in lines
        if line.component_code == "LOP"
    )

    assert basic_line.amount == Decimal("25000.00")
    assert lop_line.amount == Decimal("25000.00")
    assert lop_line.component_type == "DEDUCTION"

def test_manual_bonus_preserves_salary_components_without_double_counting(
    db,
    admin_user,
    make_employee,
):
    employee = make_employee(
        monthly_salary=Decimal("50000.00"),
    )

    assign_basic_pay(db, employee)

    hra = SalaryComponent(
        code="HRA",
        name="House Rent Allowance",
        description="Test HRA component",
        component_type="EARNING",
        calculation_type="FIXED",
        default_amount=Decimal("0.00"),
        percentage_base="BASE_PAY",
        is_variable=False,
        is_taxable=True,
        is_active=True,
        created_by_user_id=None,
    )
    db.add(hra)
    db.flush()

    db.add(
        EmployeeSalaryComponent(
            employee_id=employee.id,
            component_id=hra.id,
            amount_override=Decimal("5000.00"),
            effective_from=date(2026, 9, 1),
            effective_to=None,
            notes="HRA integration test",
            assigned_by_user_id=None,
        )
    )

    add_full_attendance(db, employee)
    db.commit()

    run = payroll_service.generate_payroll_run(
        db,
        PAYROLL_YEAR,
        PAYROLL_MONTH,
        admin_user,
    )

    record = next(
        item for item in run.records
        if item.employee_id == employee.id
    )

    payroll_service.add_payroll_adjustment(
        db,
        run.id,
        PayrollAdjustmentCreate(
            employee_id=employee.id,
            adjustment_type="EARNING",
            amount=Decimal("3000.00"),
            description="Performance bonus",
        ),
        admin_user,
    )

    db.refresh(record)

    assert record.base_pay == Decimal("25000.00")
    assert record.other_earnings == Decimal("8000.00")
    assert record.other_deductions == Decimal("0.00")
    assert record.gross_salary == Decimal("33000.00")
    assert record.net_salary == Decimal("33000.00")

    lines = list(
        db.scalars(
            select(PayrollComponentLine).where(
                PayrollComponentLine.payroll_record_id == record.id
            )
        ).all()
    )

    amounts_by_code = {
        line.component_code: line.amount
        for line in lines
    }

    assert amounts_by_code["BASIC_PAY"] == Decimal("25000.00")
    assert amounts_by_code["HRA"] == Decimal("5000.00")
    assert amounts_by_code["ADJ-1"] == Decimal("3000.00")