
from datetime import date
from decimal import Decimal

from app.models.employee_salary_component import (
    EmployeeSalaryComponent,
)
from app.models.salary_component import SalaryComponent
from app.services.salary_structure_service import (
    calculate_employee_salary_structure,
    calculate_employee_salary_structures_for_workdays,
)


def add_component(
    db,
    *,
    code,
    name,
    component_type,
    calculation_type="FIXED",
    default_amount="0.00",
    percentage_base="BASE_PAY",
    is_variable=False,
    is_taxable=True,
):
    component = SalaryComponent(
        code=code,
        name=name,
        description=None,
        component_type=component_type,
        calculation_type=calculation_type,
        default_amount=Decimal(default_amount),
        percentage_base=percentage_base,
        is_variable=is_variable,
        is_taxable=is_taxable,
        is_active=True,
        created_by_user_id=None,
    )

    db.add(component)
    db.flush()

    return component


def assign_component(
    db,
    *,
    employee_id,
    component_id,
    effective_from,
    amount_override=None,
    effective_to=None,
):
    assignment = EmployeeSalaryComponent(
        employee_id=employee_id,
        component_id=component_id,
        amount_override=amount_override,
        effective_from=effective_from,
        effective_to=effective_to,
        notes="Automated salary structure test",
        assigned_by_user_id=None,
    )

    db.add(assignment)
    db.flush()

    return assignment


def test_legacy_salary_is_used_without_component_assignments(
    db,
    make_employee,
):
    employee = make_employee(
        monthly_salary=Decimal("50000.00"),
    )

    result = calculate_employee_salary_structure(
        db=db,
        employee_id=employee.id,
        as_of_date=date(2026, 9, 1),
    )

    assert result.used_configured_structure is False
    assert result.basic_pay == Decimal("50000.00")
    assert result.monthly_earnings == Decimal("50000.00")
    assert result.monthly_deductions == Decimal("0.00")
    assert result.monthly_net_before_attendance == Decimal("50000.00")


def test_basic_pay_and_percentage_allowance_are_calculated(
    db,
    make_employee,
):
    employee = make_employee(
        monthly_salary=Decimal("50000.00"),
    )

    basic_pay = add_component(
        db,
        code="BASIC_PAY",
        name="Basic Pay",
        component_type="EARNING",
    )

    hra = add_component(
        db,
        code="HRA",
        name="House Rent Allowance",
        component_type="EARNING",
        calculation_type="PERCENTAGE",
        default_amount="20.00",
        percentage_base="BASE_PAY",
    )

    assign_component(
        db,
        employee_id=employee.id,
        component_id=basic_pay.id,
        effective_from=date(2026, 9, 1),
        amount_override=Decimal("25000.00"),
    )

    assign_component(
        db,
        employee_id=employee.id,
        component_id=hra.id,
        effective_from=date(2026, 9, 1),
    )

    result = calculate_employee_salary_structure(
        db=db,
        employee_id=employee.id,
        as_of_date=date(2026, 9, 15),
    )

    assert result.used_configured_structure is True
    assert result.basic_pay == Decimal("25000.00")
    assert result.monthly_earnings == Decimal("30000.00")
    assert result.monthly_deductions == Decimal("0.00")
    assert result.monthly_net_before_attendance == Decimal("30000.00")

    amounts = {
        component.component_code: component.amount
        for component in result.components
    }

    assert amounts["BASIC_PAY"] == Decimal("25000.00")
    assert amounts["HRA"] == Decimal("5000.00")


def test_salary_component_applies_from_its_effective_date(
    db,
    make_employee,
):
    employee = make_employee(
        monthly_salary=Decimal("50000.00"),
    )

    basic_pay = add_component(
        db,
        code="BASIC_PAY",
        name="Basic Pay",
        component_type="EARNING",
    )

    assign_component(
        db,
        employee_id=employee.id,
        component_id=basic_pay.id,
        effective_from=date(2026, 10, 15),
        amount_override=Decimal("25000.00"),
    )

    results = calculate_employee_salary_structures_for_workdays(
        db=db,
        employee_id=employee.id,
        workdays=[
            date(2026, 10, 14),
            date(2026, 10, 15),
            date(2026, 10, 16),
        ],
    )

    before = results[date(2026, 10, 14)]
    effective_day = results[date(2026, 10, 15)]
    after = results[date(2026, 10, 16)]

    assert before.used_configured_structure is False
    assert before.basic_pay == Decimal("50000.00")

    assert effective_day.used_configured_structure is True
    assert effective_day.basic_pay == Decimal("25000.00")

    assert after.used_configured_structure is True
    assert after.basic_pay == Decimal("25000.00")
