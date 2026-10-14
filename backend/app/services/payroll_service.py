
from calendar import monthrange
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.attendance import Attendance
from app.models.employee import Employee
from app.models.leave_request import LeaveRequest
from app.models.payroll_adjustment import PayrollAdjustment
from app.models.payroll_record import PayrollRecord
from app.models.payroll_run import PayrollRun
from app.models.user import User
from app.schemas.payroll import (
    PayrollAdjustmentCreate,
    PayrollAdjustmentRead,
    PayrollRecordRead,
    PayrollRunRead,
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

    employees = db.scalars(
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

    if not employees:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No eligible active employees exist for this payroll period",
        )

    employee_ids = [employee.id for employee in employees]
    monthly_workdays = len(list(iter_workdays(period_start, period_end)))

    if monthly_workdays == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No working days exist in the selected period",
        )

    attendance_rows = db.scalars(
        select(Attendance).where(
            Attendance.employee_id.in_(employee_ids),
            Attendance.attendance_date >= period_start,
            Attendance.attendance_date <= period_end,
            Attendance.check_out.is_not(None),
        )
    ).all()

    attendance_by_day: dict[tuple[int, date], Decimal] = {}

    for item in attendance_rows:
        if item.status == "HALF_DAY":
            day_value = Decimal("0.50")
        elif item.status == "PRESENT":
            day_value = Decimal("1.00")
        else:
            day_value = ZERO

        attendance_by_day[(item.employee_id, item.attendance_date)] = day_value

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

    employee_by_id = {employee.id: employee for employee in employees}

    for leave in approved_leaves:
        if not leave.leave_type.is_paid:
            continue

        employee = employee_by_id[leave.employee_id]

        leave_start = max(
            leave.start_date,
            period_start,
            employee.joining_date,
        )
        leave_end = min(leave.end_date, period_end)

        if leave_start > leave_end:
            continue

        for day in iter_workdays(leave_start, leave_end):
            paid_leave_dates.add((leave.employee_id, day))

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
            effective_start = max(period_start, employee.joining_date)
            employee_workdays = list(
                iter_workdays(effective_start, period_end)
            )

            if not employee_workdays:
                continue

            eligible_days = len(employee_workdays)
            present_days = ZERO
            paid_leave_days = ZERO
            payable_days = ZERO

            for day in employee_workdays:
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

                payable_fraction = max(
                    attendance_fraction,
                    Decimal("1.00") if paid_leave else ZERO,
                )

                payable_days += payable_fraction

            lop_days = max(
                ZERO,
                Decimal(eligible_days) - payable_days,
            )

            monthly_salary = employee.monthly_salary

            base_pay = money(
                monthly_salary
                * Decimal(eligible_days)
                / Decimal(monthly_workdays)
            )

            lop_deduction = money(
                monthly_salary
                * lop_days
                / Decimal(monthly_workdays)
            )

            db.add(
                PayrollRecord(
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
                    other_earnings=ZERO,
                    other_deductions=ZERO,
                    gross_salary=base_pay,
                    net_salary=money(base_pay - lop_deduction),
                    credit_status="PENDING",
                )
            )

        db.flush()

        if not run.records:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No employees have eligible working days in this period",
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
        select(PayrollRecord).where(
            PayrollRecord.payroll_run_id == run_id,
            PayrollRecord.employee_id == payload.employee_id,
        )
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

        adjustments = db.scalars(
            select(PayrollAdjustment).where(
                PayrollAdjustment.payroll_record_id == record.id
            )
        ).all()

        earnings = sum(
            (
                item.amount
                for item in adjustments
                if item.adjustment_type == "EARNING"
            ),
            ZERO,
        )

        deductions = sum(
            (
                item.amount
                for item in adjustments
                if item.adjustment_type == "DEDUCTION"
            ),
            ZERO,
        )

        record.other_earnings = money(earnings)
        record.other_deductions = money(deductions)
        record.gross_salary = money(record.base_pay + earnings)
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
