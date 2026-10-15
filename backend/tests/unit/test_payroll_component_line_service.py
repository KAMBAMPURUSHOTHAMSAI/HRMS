
from datetime import date
from decimal import Decimal

from app.models.payroll_adjustment import PayrollAdjustment
from app.models.payroll_component_line import PayrollComponentLine
from app.models.payroll_record import PayrollRecord
from app.models.payroll_run import PayrollRun
from app.services.payroll_component_line_service import (
    create_payroll_component_snapshot,
    list_payroll_component_lines,
)


def create_test_payroll_record(
    db,
    employee,
    admin_user,
    *,
    other_earnings=Decimal("500.00"),
    other_deductions=Decimal("200.00"),
):
    run = PayrollRun(
        year=2025,
        month=1,
        period_start=date(2025, 1, 1),
        period_end=date(2025, 1, 31),
        status="GENERATED",
        generated_by_user_id=admin_user.id,
    )

    db.add(run)
    db.flush()

    record = PayrollRecord(
        payroll_run_id=run.id,
        employee_id=employee.id,
        monthly_salary=Decimal("30000.00"),
        eligible_working_days=23,
        present_days=Decimal("22.00"),
        paid_leave_days=Decimal("0.00"),
        payable_days=Decimal("22.00"),
        lop_days=Decimal("1.00"),
        base_pay=Decimal("30000.00"),
        lop_deduction=Decimal("1000.00"),
        other_earnings=other_earnings,
        other_deductions=other_deductions,
        gross_salary=Decimal("30000.00") + other_earnings,
        net_salary=(
            Decimal("30000.00")
            + other_earnings
            - Decimal("1000.00")
            - other_deductions
        ),
        credit_status="PENDING",
    )

    db.add(record)
    db.flush()

    return run, record


def test_snapshot_preserves_payroll_amount_breakdown(
    db,
    admin_user,
    make_employee,
):
    employee = make_employee()

    _, record = create_test_payroll_record(
        db,
        employee,
        admin_user,
    )

    lines = create_payroll_component_snapshot(
        db,
        record.id,
    )

    amounts_by_code = {
        line.component_code: line.amount
        for line in lines
    }

    assert amounts_by_code["BASE_PAY"] == Decimal("30000.00")
    assert amounts_by_code["LOP"] == Decimal("1000.00")
    assert amounts_by_code["OTHER_EARNINGS"] == Decimal("500.00")
    assert amounts_by_code["OTHER_DEDUCTIONS"] == Decimal("200.00")

    # The snapshot must not change the original payroll totals.
    db.refresh(record)

    assert record.base_pay == Decimal("30000.00")
    assert record.lop_deduction == Decimal("1000.00")
    assert record.gross_salary == Decimal("30500.00")
    assert record.net_salary == Decimal("29300.00")


def test_snapshot_preserves_existing_adjustments_without_double_counting(
    db,
    admin_user,
    make_employee,
):
    employee = make_employee()

    _, record = create_test_payroll_record(
        db,
        employee,
        admin_user,
        other_earnings=Decimal("5000.00"),
        other_deductions=Decimal("500.00"),
    )

    earning = PayrollAdjustment(
        payroll_record_id=record.id,
        created_by_user_id=admin_user.id,
        adjustment_type="EARNING",
        amount=Decimal("5000.00"),
        description="Approved performance bonus",
    )

    deduction = PayrollAdjustment(
        payroll_record_id=record.id,
        created_by_user_id=admin_user.id,
        adjustment_type="DEDUCTION",
        amount=Decimal("500.00"),
        description="Other payroll deduction",
    )

    db.add_all([earning, deduction])
    db.flush()

    lines = create_payroll_component_snapshot(
        db,
        record.id,
    )

    amounts_by_code = {
        line.component_code: line.amount
        for line in lines
    }

    assert amounts_by_code["BASE_PAY"] == Decimal("30000.00")
    assert amounts_by_code["LOP"] == Decimal("1000.00")
    assert amounts_by_code[f"ADJ-{earning.id}"] == Decimal("5000.00")
    assert amounts_by_code[f"ADJ-{deduction.id}"] == Decimal("500.00")

    assert "OTHER_EARNINGS" not in amounts_by_code
    assert "OTHER_DEDUCTIONS" not in amounts_by_code


def test_repeated_snapshot_does_not_create_duplicate_lines(
    db,
    admin_user,
    make_employee,
):
    employee = make_employee()

    _, record = create_test_payroll_record(
        db,
        employee,
        admin_user,
    )

    first_snapshot = create_payroll_component_snapshot(
        db,
        record.id,
    )

    first_count = len(first_snapshot)

    second_snapshot = create_payroll_component_snapshot(
        db,
        record.id,
    )

    assert len(second_snapshot) == first_count

    persisted_lines = list_payroll_component_lines(
        db,
        record.id,
    )

    assert len(persisted_lines) == first_count
