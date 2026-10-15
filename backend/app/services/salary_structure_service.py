
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.employee_salary_component import EmployeeSalaryComponent
from app.models.salary_component import SalaryComponent
from app.models.compensation_history import CompensationHistory


CENT = Decimal("0.01")
ZERO = Decimal("0.00")


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _legacy_monthly_salary(
    db: Session,
    employee: Employee,
    as_of_date: date,
) -> Decimal:
    active_revision = db.scalar(
        select(CompensationHistory)
        .where(
            CompensationHistory.employee_id == employee.id,
            CompensationHistory.effective_from <= as_of_date,
            (
                CompensationHistory.effective_to.is_(None)
                | (CompensationHistory.effective_to >= as_of_date)
            ),
        )
        .order_by(CompensationHistory.effective_from.desc())
        .limit(1)
    )

    if active_revision is not None:
        return money(active_revision.new_monthly_salary)

    next_revision = db.scalar(
        select(CompensationHistory)
        .where(
            CompensationHistory.employee_id == employee.id,
            CompensationHistory.effective_from > as_of_date,
        )
        .order_by(CompensationHistory.effective_from.asc())
        .limit(1)
    )

    if (
        next_revision is not None
        and next_revision.previous_monthly_salary is not None
    ):
        return money(next_revision.previous_monthly_salary)

    return money(employee.monthly_salary)


@dataclass(frozen=True)
class SalaryComponentAmount:
    salary_component_id: int | None
    component_code: str
    component_name: str
    component_type: str
    amount: Decimal
    is_taxable: bool
    is_variable: bool
    calculation_details: str


@dataclass(frozen=True)
class EmployeeSalaryStructure:
    employee_id: int
    effective_date: date
    used_configured_structure: bool
    monthly_earnings: Decimal
    monthly_deductions: Decimal
    monthly_net_before_attendance: Decimal
    basic_pay: Decimal
    components: tuple[SalaryComponentAmount, ...]


def calculate_employee_salary_structure(
    db: Session,
    employee_id: int,
    as_of_date: date,
) -> EmployeeSalaryStructure:
    employee = db.get(Employee, employee_id)

    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )

    if as_of_date < employee.joining_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Salary structure cannot be calculated before joining date",
        )

    query = (
        select(EmployeeSalaryComponent, SalaryComponent)
        .join(
            SalaryComponent,
            SalaryComponent.id
            == EmployeeSalaryComponent.component_id,
        )
        .where(
            EmployeeSalaryComponent.employee_id == employee_id,
            EmployeeSalaryComponent.effective_from <= as_of_date,
            (
                EmployeeSalaryComponent.effective_to.is_(None)
                | (
                    EmployeeSalaryComponent.effective_to
                    >= as_of_date
                )
            ),
        )
        .order_by(SalaryComponent.code.asc())
    )

    rows = db.execute(query).all()

    # Backward compatibility: employees without an effective component
    # structure continue using their existing monthly salary.
    if not rows:
        legacy_salary = _legacy_monthly_salary(
             db,
            employee,
            as_of_date,
        )

        fallback = SalaryComponentAmount(
            salary_component_id=None,
            component_code="BASE_PAY",
            component_name="Base Pay",
            component_type="EARNING",
            amount=legacy_salary,
            is_taxable=True,
            is_variable=False,
            calculation_details=(
                "Legacy Employee.monthly_salary; "
                "no effective component assignments found"
            ),
        )

        return EmployeeSalaryStructure(
            employee_id=employee_id,
            effective_date=as_of_date,
            used_configured_structure=False,
            monthly_earnings=legacy_salary,
            monthly_deductions=ZERO,
            monthly_net_before_attendance=legacy_salary,
            basic_pay=legacy_salary,
            components=(fallback,),
        )

    configured = []
    basic_pay = ZERO
    pending_percentages = []

    for assignment, component in rows:
        if component.code == "BASIC_PAY":
            if component.component_type != "EARNING":
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="BASIC_PAY must be an EARNING component",
                )

            if component.calculation_type != "FIXED":
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="BASIC_PAY must use FIXED calculation",
                )

            if component.is_variable:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="BASIC_PAY cannot be a variable component",
                )

        # Variable bonuses and overtime amounts need a payroll-period
        # value; they must not be added automatically as recurring pay.
        if component.is_variable:
            configured.append(
                SalaryComponentAmount(
                    salary_component_id=component.id,
                    component_code=component.code,
                    component_name=component.name,
                    component_type=component.component_type,
                    amount=ZERO,
                    is_taxable=component.is_taxable,
                    is_variable=True,
                    calculation_details=(
                        "Variable component; amount must be calculated "
                        "or supplied for the payroll period"
                    ),
                )
            )
            continue

        configured_amount = (
            assignment.amount_override
            if assignment.amount_override is not None
            else component.default_amount
        )

        if component.calculation_type == "FIXED":
            amount = money(configured_amount)

            configured.append(
                SalaryComponentAmount(
                    salary_component_id=component.id,
                    component_code=component.code,
                    component_name=component.name,
                    component_type=component.component_type,
                    amount=amount,
                    is_taxable=component.is_taxable,
                    is_variable=False,
                    calculation_details=(
                        "Employee override"
                        if assignment.amount_override is not None
                        else "Component default amount"
                    ),
                )
            )

            if (
                component.code == "BASIC_PAY"
                and component.component_type == "EARNING"
            ):
                basic_pay += amount

        elif component.calculation_type == "PERCENTAGE":
            if configured_amount < ZERO or configured_amount > Decimal("100"):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        f"Percentage for {component.code} "
                        "must be between 0 and 100"
                    ),
                )

            pending_percentages.append(
                (assignment, component, configured_amount)
            )

        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Unsupported calculation type: "
                    f"{component.calculation_type}"
                ),
            )

    if basic_pay <= ZERO:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "An effective BASIC_PAY component with a positive "
                "amount is required for a configured salary structure"
            ),
        )

    for assignment, component, percentage in pending_percentages:
        if component.percentage_base == "BASE_PAY":
            percentage_base = basic_pay
        elif component.percentage_base == "MONTHLY_SALARY":
            percentage_base = _legacy_monthly_salary(
                db,
                employee,
                as_of_date,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Unsupported percentage base: "
                    f"{component.percentage_base}"
                ),
            )

        amount = money(
            percentage_base * percentage / Decimal("100")
        )

        configured.append(
            SalaryComponentAmount(
                salary_component_id=component.id,
                component_code=component.code,
                component_name=component.name,
                component_type=component.component_type,
                amount=amount,
                is_taxable=component.is_taxable,
                is_variable=False,
                calculation_details=(
                    f"{percentage}% of {component.percentage_base}"
                ),
            )
        )

    # Keep result order predictable for API and payslip display.
    configured.sort(key=lambda item: item.component_code)

    monthly_earnings = money(
        sum(
            (
                item.amount
                for item in configured
                if item.component_type == "EARNING"
            ),
            ZERO,
        )
    )

    monthly_deductions = money(
        sum(
            (
                item.amount
                for item in configured
                if item.component_type == "DEDUCTION"
            ),
            ZERO,
        )
    )

    return EmployeeSalaryStructure(
        employee_id=employee_id,
        effective_date=as_of_date,
        used_configured_structure=True,
        monthly_earnings=monthly_earnings,
        monthly_deductions=monthly_deductions,
        monthly_net_before_attendance=money(
            monthly_earnings - monthly_deductions
        ),
        basic_pay=money(basic_pay),
        components=tuple(configured),
    )


def calculate_employee_salary_structures_for_workdays(
    db: Session,
    employee_id: int,
    workdays: list[date],
) -> dict[date, EmployeeSalaryStructure]:
    """Resolve each workday's effective salary structure.

    Structure recalculation happens at effective-date boundaries,
    rather than running a database query for every workday.
    """
    employee = db.get(Employee, employee_id)

    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )

    days = sorted(
        set(day for day in workdays if day >= employee.joining_date)
    )

    if not days:
        return {}

    first_day = days[0]
    last_day = days[-1]

    assignments = db.scalars(
        select(EmployeeSalaryComponent).where(
            EmployeeSalaryComponent.employee_id == employee_id,
            EmployeeSalaryComponent.effective_from <= last_day,
            (
                EmployeeSalaryComponent.effective_to.is_(None)
                | (EmployeeSalaryComponent.effective_to >= first_day)
            ),
        )
    ).all()

    revisions = db.scalars(
        select(CompensationHistory).where(
            CompensationHistory.employee_id == employee_id,
            CompensationHistory.effective_from <= last_day,
            (
                CompensationHistory.effective_to.is_(None)
                | (CompensationHistory.effective_to >= first_day)
            ),
        )
    ).all()

    boundaries = {first_day}

    for item in [*assignments, *revisions]:
        start_date = item.effective_from

        if first_day < start_date <= last_day:
            boundaries.add(start_date)

        end_date = item.effective_to

        if (
            end_date is not None
            and first_day <= end_date < last_day
        ):
            boundaries.add(date.fromordinal(end_date.toordinal() + 1))

    ordered_boundaries = sorted(boundaries)
    boundary_index = 0
    current_boundary = ordered_boundaries[0]

    structure_cache: dict[date, EmployeeSalaryStructure] = {}
    result: dict[date, EmployeeSalaryStructure] = {}

    for day in days:
        while (
            boundary_index + 1 < len(ordered_boundaries)
            and ordered_boundaries[boundary_index + 1] <= day
        ):
            boundary_index += 1
            current_boundary = ordered_boundaries[boundary_index]

        if current_boundary not in structure_cache:
            structure_cache[current_boundary] = (
                calculate_employee_salary_structure(
                    db=db,
                    employee_id=employee_id,
                    as_of_date=current_boundary,
                )
            )

        result[day] = structure_cache[current_boundary]

    return result
