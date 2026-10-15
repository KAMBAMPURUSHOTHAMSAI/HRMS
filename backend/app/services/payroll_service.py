
from calendar import monthrange
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.attendance import Attendance
from app.models.employee import Employee
from app.models.holiday import Holiday
from app.models.holiday_selection import HolidaySelection
from app.models.leave_request import LeaveRequest
from app.models.payroll_adjustment import PayrollAdjustment
from app.models.payroll_component_line import PayrollComponentLine
from app.models.payroll_record import PayrollRecord
from app.models.payroll_run import PayrollRun
from app.models.shift import Shift
from app.models.shift_assignment import ShiftAssignment
from app.models.user import User
from app.schemas.payroll import (
    PayrollAdjustmentCreate,
    PayrollAdjustmentRead,
    PayrollRecordRead,
    PayrollRunRead,
)
from app.services.salary_structure_service import (
    calculate_employee_salary_structures_for_workdays,
)


COMPANY_TIMEZONE = ZoneInfo("Asia/Kolkata")
CENT = Decimal("0.01")
ZERO = Decimal("0.00")


def company_today() -> date:
    return datetime.now(COMPANY_TIMEZONE).date()


def now_local() -> datetime:
    return datetime.now(COMPANY_TIMEZONE)


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def iter_workdays(start: date, end: date):
    """Yield weekdays, Monday through Friday."""
    current = start

    while current <= end:
        if current.weekday() < 5:
            yield current

        current = date.fromordinal(current.toordinal() + 1)


def completed_period(year: int, month: int) -> tuple[date, date]:
    last_day_number = monthrange(year, month)[1]
    period_start = date(year, month, 1)
    period_end = date(year, month, last_day_number)

    if period_end >= company_today():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Payroll can only be generated for a completed month",
        )

    return period_start, period_end


def payroll_run_query():
    return select(PayrollRun).options(
        selectinload(PayrollRun.records)
        .selectinload(PayrollRecord.employee)
        .selectinload(Employee.user),
        selectinload(PayrollRun.records)
        .selectinload(PayrollRecord.adjustments),
        selectinload(PayrollRun.records)
        .selectinload(PayrollRecord.component_lines),
    )


def get_payroll_run(db: Session, run_id: int) -> PayrollRun:
    run = db.scalar(
        payroll_run_query().where(PayrollRun.id == run_id)
    )

    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payroll run not found",
        )

    return run


def serialize_payroll_run(run: PayrollRun) -> PayrollRunRead:
    records = list(run.records)

    gross = sum(
        (record.gross_salary for record in records),
        ZERO,
    )
    lop = sum(
        (record.lop_deduction for record in records),
        ZERO,
    )
    other_deductions = sum(
        (record.other_deductions for record in records),
        ZERO,
    )
    net = sum(
        (record.net_salary for record in records),
        ZERO,
    )

    return PayrollRunRead(
        id=run.id,
        year=run.year,
        month=run.month,
        period_start=run.period_start,
        period_end=run.period_end,
        status=run.status,
        generated_by_user_id=run.generated_by_user_id,
        locked_by_user_id=run.locked_by_user_id,
        generated_at=run.generated_at,
        locked_at=run.locked_at,
        record_count=len(records),
        total_gross_salary=money(gross),
        total_lop_deduction=money(lop),
        total_deductions=money(lop + other_deductions),
        total_net_salary=money(net),
    )


def serialize_payroll_record(
    record: PayrollRecord,
) -> PayrollRecordRead:
    employee = record.employee
    user = employee.user

    return PayrollRecordRead(
        id=record.id,
        payroll_run_id=record.payroll_run_id,
        employee_id=record.employee_id,
        employee_code=employee.employee_code,
        employee_name=f"{user.first_name} {user.last_name}",
        employee_email=user.email,
        year=record.payroll_run.year,
        month=record.payroll_run.month,
        monthly_salary=record.monthly_salary,
        eligible_working_days=record.eligible_working_days,
        present_days=record.present_days,
        paid_leave_days=record.paid_leave_days,
        payable_days=record.payable_days,
        lop_days=record.lop_days,
        base_pay=record.base_pay,
        lop_deduction=record.lop_deduction,
        other_earnings=record.other_earnings,
        other_deductions=record.other_deductions,
        gross_salary=record.gross_salary,
        net_salary=record.net_salary,
        credit_status=record.credit_status,
        simulated_credit_at=record.simulated_credit_at,
        created_at=record.created_at,
    )


def _load_holiday_dates_by_employee(
    db: Session,
    employees: list[Employee],
    period_start: date,
    period_end: date,
) -> dict[int, set[date]]:
    """Return applicable active holidays for each employee.

    Company holidays apply to everyone, regional holidays match the
    employee region case-insensitively, and optional holidays apply only
    when the employee has selected them.
    """
    if not employees:
        return {}

    employee_ids = [employee.id for employee in employees]
    holidays = list(
        db.scalars(
            select(Holiday).where(
                Holiday.is_active.is_(True),
                Holiday.holiday_date >= period_start,
                Holiday.holiday_date <= period_end,
            )
        ).all()
    )

    selected_holidays_by_employee: dict[int, set[int]] = {
        employee_id: set() for employee_id in employee_ids
    }
    selections = db.scalars(
        select(HolidaySelection).where(
            HolidaySelection.employee_id.in_(employee_ids),
            HolidaySelection.status == "SELECTED",
        )
    ).all()

    for selection in selections:
        selected_holidays_by_employee.setdefault(
            selection.employee_id, set()
        ).add(selection.holiday_id)

    result: dict[int, set[date]] = {}

    for employee in employees:
        applicable_dates: set[date] = set()
        employee_region = (employee.region or "").strip().casefold()
        selected_ids = selected_holidays_by_employee.get(employee.id, set())

        for holiday in holidays:
            if holiday.holiday_type == "COMPANY":
                applicable_dates.add(holiday.holiday_date)
            elif (
                holiday.holiday_type == "REGIONAL"
                and employee_region
                and (holiday.region or "").strip().casefold() == employee_region
            ):
                applicable_dates.add(holiday.holiday_date)
            elif (
                holiday.holiday_type == "OPTIONAL"
                and holiday.id in selected_ids
            ):
                applicable_dates.add(holiday.holiday_date)

        result[employee.id] = applicable_dates

    return result


def _load_attendance_fractions(
    db: Session,
    employee_ids: list[int],
    period_start: date,
    period_end: date,
) -> dict[tuple[int, date], Decimal]:
    rows = db.scalars(
        select(Attendance).where(
            Attendance.employee_id.in_(employee_ids),
            Attendance.attendance_date >= period_start,
            Attendance.attendance_date <= period_end,
            Attendance.check_out.is_not(None),
        )
    ).all()

    attendance_by_day: dict[tuple[int, date], Decimal] = {}

    for item in rows:
        if item.status == "HALF_DAY":
            day_value = Decimal("0.50")
        elif item.status == "PRESENT":
            day_value = Decimal("1.00")
        else:
            day_value = ZERO

        attendance_by_day[
            (item.employee_id, item.attendance_date)
        ] = day_value

    return attendance_by_day



def _load_shift_overtime_by_employee_day(
    db: Session,
    employees: list[Employee],
    period_start: date,
    period_end: date,
) -> dict[tuple[int, date], dict[str, object]]:
    """Calculate overtime minutes from completed attendance using the effective shift.

    Formula mirrors shift reporting: overtime = max(0, elapsed working minutes
    minus shift break minutes minus expected shift working minutes). Employee-
    specific assignments override department assignments; inactive shifts are ignored.
    """
    if not employees:
        return {}

    employee_ids = [employee.id for employee in employees]
    employee_by_id = {employee.id: employee for employee in employees}
    department_ids = sorted({
        employee.department_id
        for employee in employees
        if employee.department_id is not None
    })

    attendance_rows = list(db.scalars(
        select(Attendance).where(
            Attendance.employee_id.in_(employee_ids),
            Attendance.attendance_date >= period_start,
            Attendance.attendance_date <= period_end,
            Attendance.check_out.is_not(None),
        )
    ).all())
    if not attendance_rows:
        return {}

    assignment_scope = [ShiftAssignment.employee_id.in_(employee_ids)]
    if department_ids:
        assignment_scope.append(
            and_(
                ShiftAssignment.employee_id.is_(None),
                ShiftAssignment.department_id.in_(department_ids),
            )
        )

    # ShiftAssignment is defined in its own module and does not expose a
    # SQLAlchemy `shift` relationship in this project. Load Shift records by
    # shift_id explicitly so payroll does not depend on a missing relationship.
    assignments = list(db.scalars(
        select(ShiftAssignment).where(
            ShiftAssignment.effective_from <= period_end,
            or_(
                ShiftAssignment.effective_to.is_(None),
                ShiftAssignment.effective_to >= period_start,
            ),
            or_(*assignment_scope),
        )
    ).all())
    shift_ids = sorted({assignment.shift_id for assignment in assignments})
    shifts_by_id = {}
    if shift_ids:
        shifts_by_id = {
            shift.id: shift
            for shift in db.scalars(select(Shift).where(Shift.id.in_(shift_ids))).all()
        }

    result: dict[tuple[int, date], dict[str, object]] = {}

    for attendance in attendance_rows:
        employee = employee_by_id.get(attendance.employee_id)
        if employee is None or attendance.check_in is None:
            continue
        if (attendance.status or "").upper() not in {"PRESENT", "HALF_DAY"}:
            continue

        attendance_date = attendance.attendance_date
        matching_assignments = [
            assignment
            for assignment in assignments
            if assignment.effective_from <= attendance_date
            and (
                assignment.effective_to is None
                or assignment.effective_to >= attendance_date
            )
            and (
                assignment.employee_id == employee.id
                or (
                    assignment.employee_id is None
                    and employee.department_id is not None
                    and assignment.department_id == employee.department_id
                )
            )
        ]
        if not matching_assignments:
            continue

        # Employee-level assignments always take priority over department defaults.
        matching_assignments.sort(
            key=lambda assignment: (
                assignment.employee_id == employee.id,
                assignment.effective_from,
                assignment.id,
            ),
            reverse=True,
        )
        shift = shifts_by_id.get(matching_assignments[0].shift_id)
        if shift is None or not shift.is_active:
            continue

        expected_work_minutes = int(
            getattr(shift, "expected_work_minutes", 480) or 480
        )
        break_minutes = int(getattr(shift, "break_minutes", 0) or 0)
        multiplier = Decimal(
            str(getattr(shift, "overtime_multiplier", Decimal("1.50")) or 0)
        )
        worked_minutes = int(
            attendance.working_minutes
            if attendance.working_minutes is not None
            else (
                (attendance.check_out - attendance.check_in).total_seconds() // 60
            )
        )

        if expected_work_minutes <= 0 or multiplier <= ZERO:
            continue

        overtime_minutes = max(
            0,
            worked_minutes - break_minutes - expected_work_minutes,
        )
        if overtime_minutes <= 0:
            continue

        result[(employee.id, attendance_date)] = {
            "minutes": overtime_minutes,
            "expected_work_minutes": expected_work_minutes,
            "multiplier": multiplier,
            "shift_name": shift.name,
        }

    return result


def _load_paid_leave_dates(
    db: Session,
    employees: list[Employee],
    period_start: date,
    period_end: date,
    holiday_dates_by_employee: dict[int, set[date]],
) -> set[tuple[int, date]]:
    employee_ids = [employee.id for employee in employees]

    approved_leaves = db.scalars(
        select(LeaveRequest)
        .options(selectinload(LeaveRequest.leave_type))
        .where(
            LeaveRequest.employee_id.in_(employee_ids),
            LeaveRequest.status == "APPROVED",
            LeaveRequest.start_date <= period_end,
            LeaveRequest.end_date >= period_start,
        )
    ).all()

    paid_leave_dates: set[tuple[int, date]] = set()
    employee_by_id = {
        employee.id: employee for employee in employees
    }

    for leave in approved_leaves:
        if not leave.leave_type.is_paid:
            continue

        employee = employee_by_id.get(leave.employee_id)

        if employee is None:
            continue

        leave_start = max(
            leave.start_date,
            period_start,
            employee.joining_date,
        )
        leave_end = min(leave.end_date, period_end)

        if leave_start > leave_end:
            continue

        employee_holidays = holiday_dates_by_employee.get(
            leave.employee_id, set()
        )
        for day in iter_workdays(leave_start, leave_end):
            # A holiday is not consumed as a paid-leave workday.
            if day not in employee_holidays:
                paid_leave_dates.add((leave.employee_id, day))

    return paid_leave_dates


def generate_payroll_run(
    db: Session,
    year: int,
    month: int,
    generator: User,
) -> PayrollRun:
    period_start, period_end = completed_period(year, month)

    existing_run = db.scalar(
        select(PayrollRun).where(
            PayrollRun.year == year,
            PayrollRun.month == month,
        )
    )

    if existing_run is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Payroll has already been generated for this month",
        )

    employees = list(
        db.scalars(
            select(Employee)
            .join(User, Employee.user_id == User.id)
            .options(selectinload(Employee.user))
            .where(
                Employee.employment_status == "ACTIVE",
                Employee.joining_date <= period_end,
                User.is_active.is_(True),
            )
            .order_by(Employee.id)
        ).all()
    )

    if not employees:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "No eligible active employees exist for this payroll period"
            ),
        )

    employee_ids = [employee.id for employee in employees]

    # Weekdays before employee-specific holidays are excluded. Each employee
    # receives their own denominator because regional and optional holidays
    # can differ by employee.
    calendar_workdays = list(iter_workdays(period_start, period_end))
    monthly_workdays = len(calendar_workdays)

    if monthly_workdays == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No working days exist in the selected period",
        )

    attendance_by_day = _load_attendance_fractions(
        db=db,
        employee_ids=employee_ids,
        period_start=period_start,
        period_end=period_end,
    )

    holiday_dates_by_employee = _load_holiday_dates_by_employee(
        db=db,
        employees=employees,
        period_start=period_start,
        period_end=period_end,
    )

    paid_leave_dates = _load_paid_leave_dates(
        db=db,
        employees=employees,
        period_start=period_start,
        period_end=period_end,
        holiday_dates_by_employee=holiday_dates_by_employee,
    )

    # Overtime is resolved from attendance plus the effective employee/department shift.
    overtime_by_day = _load_shift_overtime_by_employee_day(
        db=db,
        employees=employees,
        period_start=period_start,
        period_end=period_end,
    )

    run = PayrollRun(
        year=year,
        month=month,
        period_start=period_start,
        period_end=period_end,
        status="GENERATED",
        generated_by_user_id=generator.id,
    )

    db.add(run)

    try:
        db.flush()

        for employee in employees:
            effective_start = max(
                period_start,
                employee.joining_date,
            )
            employee_holidays = holiday_dates_by_employee.get(
                employee.id, set()
            )
            employee_month_workdays = [
                day
                for day in calendar_workdays
                if day not in employee_holidays
            ]
            monthly_workdays_for_employee = len(employee_month_workdays)
            employee_workdays = [
                day
                for day in employee_month_workdays
                if day >= effective_start
            ]

            if not employee_workdays:
                continue

            if monthly_workdays_for_employee == 0:
                continue

            eligible_days = len(employee_workdays)

            # Every workday is resolved against the salary component
            # assignments and compensation history effective on that date.
            structures_by_day = (
                calculate_employee_salary_structures_for_workdays(
                    db=db,
                    employee_id=employee.id,
                    workdays=employee_workdays,
                )
            )

            # If overtime was worked on a weekend/holiday, resolve the salary
            # structure on that date as well; the day remains excluded from the
            # normal working-day and LOP denominator.
            employee_overtime_days = sorted(
                overtime_day
                for overtime_employee_id, overtime_day in overtime_by_day
                if overtime_employee_id == employee.id
                and overtime_day >= employee.joining_date
            )
            missing_overtime_days = [
                overtime_day
                for overtime_day in employee_overtime_days
                if overtime_day not in structures_by_day
            ]
            if missing_overtime_days:
                structures_by_day.update(
                    calculate_employee_salary_structures_for_workdays(
                        db=db,
                        employee_id=employee.id,
                        workdays=missing_overtime_days,
                    )
                )

            present_days = ZERO
            paid_leave_days = ZERO
            payable_days = ZERO

            monthly_salary_basis_total = ZERO
            lop_amount_total = ZERO

            component_totals: dict[
                tuple[int | None, str, str, str, bool],
                Decimal,
            ] = {}

            component_details: dict[
                tuple[int | None, str, str, str, bool],
                set[str],
            ] = {}
            overtime_pay_total = ZERO
            overtime_detail_items: list[str] = []
            overtime_total_minutes = 0

            for day in employee_workdays:
                structure = structures_by_day[day]

                # Monthly gross basis effective on this date.
                monthly_salary_basis_total += (
                    structure.monthly_earnings
                )

                attendance_fraction = attendance_by_day.get(
                    (employee.id, day),
                    ZERO,
                )

                paid_leave = (
                    (employee.id, day) in paid_leave_dates
                )

                present_days += attendance_fraction

                if paid_leave:
                    paid_leave_days += Decimal("1.00")

                # Paid leave protects the day from LOP. A half-day
                # attendance contributes 0.5 unless covered by paid leave.
                payable_fraction = max(
                    attendance_fraction,
                    Decimal("1.00") if paid_leave else ZERO,
                )

                payable_days += payable_fraction

                unpaid_fraction = max(
                    ZERO,
                    Decimal("1.00") - payable_fraction,
                )

                # LOP is deducted from recurring earnings for unpaid days.
                lop_amount_total += (
                    structure.monthly_earnings
                    * unpaid_fraction
                    / Decimal(monthly_workdays_for_employee)
                )

                for component in structure.components:
                    # A stable component identity is used to combine daily
                    # amounts when a salary revision occurs mid-month.
                    key = (
                        component.salary_component_id,
                        component.component_code,
                        component.component_name,
                        component.component_type,
                        component.is_taxable,
                    )

                    daily_amount = (
                        component.amount / Decimal(monthly_workdays_for_employee)
                    )

                    if component.component_type == "DEDUCTION":
                        # Recurring deductions are prorated to payable days.
                        daily_amount *= payable_fraction

                    component_totals[key] = (
                        component_totals.get(key, ZERO)
                        + daily_amount
                    )

                    component_details.setdefault(key, set()).add(
                        component.calculation_details
                    )

            # Overtime pay is based on the day's effective Basic Pay, the
            # employee-specific month's working-day denominator, and the
            # overtime multiplier of the applicable shift.
            for overtime_day in employee_overtime_days:
                overtime_data = overtime_by_day.get((employee.id, overtime_day))
                if not overtime_data:
                    continue

                structure = structures_by_day.get(overtime_day)
                if structure is None or structure.basic_pay <= ZERO:
                    continue

                minutes = int(overtime_data["minutes"])
                expected_minutes = int(overtime_data["expected_work_minutes"])
                multiplier = Decimal(str(overtime_data["multiplier"]))
                if minutes <= 0 or expected_minutes <= 0 or multiplier <= ZERO:
                    continue

                daily_basic_pay = (
                    structure.basic_pay / Decimal(monthly_workdays_for_employee)
                )
                day_overtime_pay = (
                    daily_basic_pay
                    * Decimal(minutes)
                    * multiplier
                    / Decimal(expected_minutes)
                )
                overtime_pay_total += day_overtime_pay
                overtime_total_minutes += minutes
                overtime_detail_items.append(
                    f"{overtime_data['shift_name']}: {minutes} min at {multiplier}x"
                )

            lop_days = max(
                ZERO,
                Decimal(eligible_days) - payable_days,
            )

            # Use an average monthly gross basis when the salary changes
            # during the payroll month. Existing employees without a
            # configured structure retain Employee.monthly_salary behavior.
            monthly_salary = money(
                monthly_salary_basis_total / Decimal(eligible_days)
            )

            base_pay = ZERO
            other_earnings = ZERO
            other_deductions = ZERO

            component_line_data: list[dict] = []

            for key, raw_amount in component_totals.items():
                (
                    component_id,
                    component_code,
                    component_name,
                    component_type,
                    is_taxable,
                ) = key

                amount = money(raw_amount)

                if component_type == "EARNING":
                    if component_code in {"BASE_PAY", "BASIC_PAY"}:
                        base_pay += amount
                    else:
                        other_earnings += amount

                elif component_type == "DEDUCTION":
                    other_deductions += amount

                details = sorted(
                    detail
                    for detail in component_details.get(key, set())
                    if detail
                )

                component_line_data.append(
                    {
                        "salary_component_id": component_id,
                        "component_code": component_code,
                        "component_name": component_name,
                        "component_type": component_type,
                        "amount": amount,
                        "is_taxable": is_taxable,
                        "calculation_details": "; ".join(details)
                        or "Effective-dated salary component",
                    }
                )

            base_pay = money(base_pay)
            other_earnings = money(other_earnings)
            other_deductions = money(other_deductions)
            lop_deduction = money(lop_amount_total)
            overtime_pay = money(overtime_pay_total)

            if overtime_pay > ZERO:
                overtime_hours = (
                    Decimal(overtime_total_minutes) / Decimal("60")
                ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                other_earnings = money(other_earnings + overtime_pay)
                component_line_data.append(
                    {
                        "salary_component_id": None,
                        "component_code": "SHIFT_OVERTIME",
                        "component_name": "Shift Overtime Pay",
                        "component_type": "EARNING",
                        "amount": overtime_pay,
                        "is_taxable": True,
                        "calculation_details": (
                            f"{overtime_hours} hours; "
                            + "; ".join(overtime_detail_items)
                        ),
                    }
                )

            gross_salary = money(
                base_pay + other_earnings
            )

            net_salary = money(
                gross_salary
                - lop_deduction
                - other_deductions
            )

            if net_salary < ZERO:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        "Configured deductions exceed net earnings for "
                        f"employee {employee.id}. Review the salary structure."
                    ),
                )

            record = PayrollRecord(
                payroll_run_id=run.id,
                employee_id=employee.id,
                monthly_salary=monthly_salary,
                eligible_working_days=eligible_days,
                present_days=present_days,
                paid_leave_days=paid_leave_days,
                payable_days=payable_days,
                lop_days=lop_days,
                base_pay=base_pay,
                lop_deduction=lop_deduction,
                other_earnings=other_earnings,
                other_deductions=other_deductions,
                gross_salary=gross_salary,
                net_salary=net_salary,
                credit_status="PENDING",
            )

            db.add(record)
            db.flush()

            # Historical snapshot: these lines record the component
            # amounts used for this payroll and do not recalculate later.
            for line_data in component_line_data:
                db.add(
                    PayrollComponentLine(
                        payroll_record_id=record.id,
                        **line_data,
                    )
                )

            if lop_deduction > ZERO:
                db.add(
                    PayrollComponentLine(
                        payroll_record_id=record.id,
                        salary_component_id=None,
                        component_code="LOP",
                        component_name="Loss of Pay Deduction",
                        component_type="DEDUCTION",
                        amount=lop_deduction,
                        is_taxable=False,
                        calculation_details=(
                            f"Unpaid days: {lop_days} of "
                            f"{eligible_days} eligible working days"
                        ),
                    )
                )

        db.flush()

        if not run.records:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "No employees have eligible working days in this period"
                ),
            )

        run_id = run.id
        db.commit()

        return get_payroll_run(db, run_id)

    except Exception:
        db.rollback()
        raise


def list_payroll_runs(db: Session) -> list[PayrollRun]:
    statement = (
        payroll_run_query()
        .order_by(PayrollRun.year.desc(), PayrollRun.month.desc())
    )

    return list(db.scalars(statement).all())


def list_run_records(
    db: Session,
    run_id: int,
) -> list[PayrollRecord]:
    run = get_payroll_run(db, run_id)
    return sorted(run.records, key=lambda record: record.employee_id)


def list_my_payroll_records(
    db: Session,
    user: User,
) -> list[PayrollRecord]:
    employee = user.employee

    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile is not configured for this account",
        )

    statement = (
        select(PayrollRecord)
        .join(PayrollRun)
        .where(PayrollRecord.employee_id == employee.id)
        .options(
            selectinload(PayrollRecord.employee)
            .selectinload(Employee.user),
            selectinload(PayrollRecord.payroll_run),
            selectinload(PayrollRecord.component_lines),
        )
        .order_by(PayrollRun.year.desc(), PayrollRun.month.desc())
    )

    return list(db.scalars(statement).all())


def add_payroll_adjustment(
    db: Session,
    run_id: int,
    payload: PayrollAdjustmentCreate,
    actor: User,
) -> PayrollAdjustment:
    run = db.scalar(
        select(PayrollRun)
        .where(PayrollRun.id == run_id)
        .with_for_update()
    )

    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payroll run not found",
        )

    if run.status != "GENERATED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Payroll adjustments are not allowed after locking",
        )

    record = db.scalar(
        select(PayrollRecord)
        .where(
            PayrollRecord.payroll_run_id == run_id,
            PayrollRecord.employee_id == payload.employee_id,
        )
        .with_for_update()
    )

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee payroll record not found in this run",
        )

    adjustment = PayrollAdjustment(
        payroll_record_id=record.id,
        created_by_user_id=actor.id,
        adjustment_type=payload.adjustment_type,
        amount=payload.amount,
        description=payload.description.strip(),
    )

    try:
        db.add(adjustment)
        db.flush()

        adjustments = list(
            db.scalars(
                select(PayrollAdjustment).where(
                    PayrollAdjustment.payroll_record_id == record.id
                )
            ).all()
        )

        component_lines = list(
            db.scalars(
                select(PayrollComponentLine).where(
                    PayrollComponentLine.payroll_record_id == record.id
                )
            ).all()
        )

        # Salary component lines exclude Basic Pay, LOP and previous
        # adjustment snapshots, so totals are not counted more than once.
        component_earnings = sum(
            (
                line.amount
                for line in component_lines
                if line.component_type == "EARNING"
                and line.component_code not in {"BASE_PAY", "BASIC_PAY"}
                and not line.component_code.startswith("ADJ-")
            ),
            ZERO,
        )

        component_deductions = sum(
            (
                line.amount
                for line in component_lines
                if line.component_type == "DEDUCTION"
                and line.component_code != "LOP"
                and not line.component_code.startswith("ADJ-")
            ),
            ZERO,
        )

        adjustment_earnings = sum(
            (
                item.amount
                for item in adjustments
                if item.adjustment_type == "EARNING"
            ),
            ZERO,
        )

        adjustment_deductions = sum(
            (
                item.amount
                for item in adjustments
                if item.adjustment_type == "DEDUCTION"
            ),
            ZERO,
        )

        record.other_earnings = money(
            component_earnings + adjustment_earnings
        )

        record.other_deductions = money(
            component_deductions + adjustment_deductions
        )

        record.gross_salary = money(
            record.base_pay + record.other_earnings
        )

        record.net_salary = money(
            record.gross_salary
            - record.lop_deduction
            - record.other_deductions
        )

        if record.net_salary < ZERO:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Adjustments cannot make net salary negative",
            )

        # Rebuild adjustment snapshot rows so repeatedly adding adjustments
        # never duplicates an adjustment in the payslip breakdown.
        for line in component_lines:
            if line.component_code.startswith("ADJ-"):
                db.delete(line)

        db.flush()

        for item in adjustments:
            db.add(
                PayrollComponentLine(
                    payroll_record_id=record.id,
                    salary_component_id=None,
                    component_code=f"ADJ-{item.id}",
                    component_name=item.description[:150],
                    component_type=item.adjustment_type,
                    amount=item.amount,
                    is_taxable=False,
                    calculation_details=item.description,
                )
            )

        db.commit()
        db.refresh(adjustment)

        return adjustment

    except Exception:
        db.rollback()
        raise


def lock_payroll(
    db: Session,
    run_id: int,
    actor: User,
) -> PayrollRun:
    run = db.scalar(
        select(PayrollRun)
        .where(PayrollRun.id == run_id)
        .with_for_update()
    )

    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payroll run not found",
        )

    if run.status != "GENERATED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Payroll run is already locked",
        )

    run.status = "LOCKED"
    run.locked_by_user_id = actor.id
    run.locked_at = now_local()

    db.commit()

    return get_payroll_run(db, run_id)


def simulate_salary_credit(
    db: Session,
    run_id: int,
) -> PayrollRun:
    run = db.scalar(
        payroll_run_query()
        .where(PayrollRun.id == run_id)
        .with_for_update()
    )

    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payroll run not found",
        )

    if run.status != "LOCKED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Lock the payroll run before simulating salary credit",
        )

    if not run.records:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This payroll run has no records",
        )

    if any(
        record.credit_status == "SIMULATED"
        for record in run.records
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Salary credit was already simulated",
        )

    simulated_at = now_local()

    for record in run.records:
        record.credit_status = "SIMULATED"
        record.simulated_credit_at = simulated_at

    db.commit()

    return get_payroll_run(db, run_id)


def serialize_adjustment(
    adjustment: PayrollAdjustment,
) -> PayrollAdjustmentRead:
    return PayrollAdjustmentRead(
        id=adjustment.id,
        payroll_record_id=adjustment.payroll_record_id,
        created_by_user_id=adjustment.created_by_user_id,
        adjustment_type=adjustment.adjustment_type,
        amount=adjustment.amount,
        description=adjustment.description,
        created_at=adjustment.created_at,
    )
