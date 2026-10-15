
from calendar import monthrange
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.attendance import Attendance
from app.models.employee import Employee
from app.models.holiday import Holiday
from app.models.holiday_selection import HolidaySelection
from app.models.user import User
from app.schemas.attendance import (
    AttendanceCorrection,
    AttendanceRead,
    AttendanceSummary,
)


COMPANY_TIMEZONE = ZoneInfo("Asia/Kolkata")


def company_now() -> datetime:
    return datetime.now(COMPANY_TIMEZONE)


def get_current_employee(user: User) -> Employee:
    employee = user.employee

    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile is not configured for this account",
        )

    if not user.is_active or employee.employment_status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive employees cannot record attendance",
        )

    return employee


def _get_employee_holiday_dates(
    db: Session,
    employee: Employee,
    start_date: date,
    end_date: date,
) -> set[date]:
    """
    Return the unique holiday dates applicable to an employee.

    COMPANY holidays apply to everyone.
    REGIONAL holidays apply when the employee's region matches.
    OPTIONAL holidays apply only when the employee selected them.
    Inactive holidays are ignored.
    """
    applicable_types = [
        Holiday.holiday_type == "COMPANY",
    ]

    employee_region = (employee.region or "").strip()

    if employee_region:
        applicable_types.append(
            and_(
                Holiday.holiday_type == "REGIONAL",
                func.lower(func.trim(Holiday.region))
                == employee_region.lower(),
            )
        )

    company_and_regional_statement = select(
        Holiday.holiday_date
    ).where(
        Holiday.is_active.is_(True),
        Holiday.holiday_date >= start_date,
        Holiday.holiday_date <= end_date,
        or_(*applicable_types),
    )

    holiday_dates = set(
        db.scalars(company_and_regional_statement).all()
    )

    # Optional holidays count only for active employee selections.
    optional_statement = (
        select(Holiday.holiday_date)
        .join(
            HolidaySelection,
            HolidaySelection.holiday_id == Holiday.id,
        )
        .where(
            Holiday.is_active.is_(True),
            Holiday.holiday_type == "OPTIONAL",
            HolidaySelection.employee_id == employee.id,
            HolidaySelection.status == "SELECTED",
            Holiday.holiday_date >= start_date,
            Holiday.holiday_date <= end_date,
        )
    )

    holiday_dates.update(
        db.scalars(optional_statement).all()
    )

    return holiday_dates


def check_in(db: Session, user: User) -> Attendance:
    employee = get_current_employee(user)
    now = company_now()

    existing = db.scalar(
        select(Attendance).where(
            Attendance.employee_id == employee.id,
            Attendance.attendance_date == now.date(),
        )
    )

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Attendance has already been recorded for today",
        )

    record = Attendance(
        employee_id=employee.id,
        attendance_date=now.date(),
        check_in=now,
        status="PRESENT",
    )

    db.add(record)

    try:
        db.commit()
        db.refresh(record)
        return record
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Attendance has already been recorded for today",
        ) from None


def check_out(db: Session, user: User) -> Attendance:
    employee = get_current_employee(user)
    now = company_now()

    record = db.scalar(
        select(Attendance).where(
            Attendance.employee_id == employee.id,
            Attendance.attendance_date == now.date(),
        )
    )

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Check in before checking out",
        )

    if record.check_out is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Attendance has already been checked out",
        )

    if now <= record.check_in:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Check-out time must be after check-in time",
        )

    record.check_out = now
    record.working_minutes = int(
        (now - record.check_in).total_seconds() // 60
    )

    try:
        db.commit()
        db.refresh(record)
        return record
    except Exception:
        db.rollback()
        raise


def get_my_attendance(
    db: Session,
    user: User,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[Attendance]:
    employee = get_current_employee(user)

    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="start_date cannot be after end_date",
        )

    statement = select(Attendance).where(
        Attendance.employee_id == employee.id
    )

    if start_date is not None:
        statement = statement.where(
            Attendance.attendance_date >= start_date
        )

    if end_date is not None:
        statement = statement.where(
            Attendance.attendance_date <= end_date
        )

    statement = statement.order_by(
        Attendance.attendance_date.desc()
    )

    return list(db.scalars(statement).all())


def get_my_monthly_summary(
    db: Session,
    user: User,
    year: int,
    month: int,
) -> AttendanceSummary:
    employee = get_current_employee(user)

    if year < 1 or month < 1 or month > 12:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid year or month",
        )

    first_day = date(year, month, 1)
    last_day = date(
        year,
        month,
        monthrange(year, month)[1],
    )

    records = list(
        db.scalars(
            select(Attendance).where(
                Attendance.employee_id == employee.id,
                Attendance.attendance_date >= first_day,
                Attendance.attendance_date <= last_day,
            )
        ).all()
    )

    total_minutes = sum(
        record.working_minutes or 0
        for record in records
    )

    present_days = sum(
        1
        for record in records
        if (record.status or "").upper() == "PRESENT"
    )

    half_days = sum(
        1
        for record in records
        if (record.status or "").upper() == "HALF_DAY"
    )

    holiday_dates = _get_employee_holiday_dates(
        db,
        employee,
        first_day,
        last_day,
    )

    # Count standard Monday-Friday working days.
    weekdays_in_month = sum(
        1
        for day_number in range(1, last_day.day + 1)
        if date(year, month, day_number).weekday() < 5
    )

    # A holiday reduces scheduled working days only when
    # it falls on a standard weekday.
    weekday_holidays = sum(
        1
        for holiday_date in holiday_dates
        if holiday_date.weekday() < 5
    )

    scheduled_working_days = max(
        0,
        weekdays_in_month - weekday_holidays,
    )

    non_holiday_recorded_days = sum(
        1
        for record in records
        if record.attendance_date not in holiday_dates
    )

    return AttendanceSummary(
        year=year,
        month=month,
        days_recorded=len(records),
        present_days=present_days,
        half_days=half_days,
        total_worked_minutes=total_minutes,
        total_worked_hours=(
            Decimal(total_minutes) / Decimal("60")
        ).quantize(Decimal("0.01")),
        holiday_days=len(holiday_dates),
        scheduled_working_days=scheduled_working_days,
        non_holiday_recorded_days=non_holiday_recorded_days,
    )


def list_all_attendance(
    db: Session,
    employee_id: int | None = None,
    department_id: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Attendance]:
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="start_date cannot be after end_date",
        )

    statement = (
        select(Attendance)
        .join(Employee, Attendance.employee_id == Employee.id)
        .options(selectinload(Attendance.employee))
    )

    if employee_id is not None:
        statement = statement.where(
            Attendance.employee_id == employee_id
        )

    if department_id is not None:
        statement = statement.where(
            Employee.department_id == department_id
        )

    if start_date is not None:
        statement = statement.where(
            Attendance.attendance_date >= start_date
        )

    if end_date is not None:
        statement = statement.where(
            Attendance.attendance_date <= end_date
        )

    statement = (
        statement
        .order_by(
            Attendance.attendance_date.desc(),
            Attendance.employee_id,
        )
        .offset(skip)
        .limit(limit)
    )

    return list(db.scalars(statement).all())


def correct_attendance(
    db: Session,
    attendance_id: int,
    payload: AttendanceCorrection,
    admin_user: User,
) -> Attendance:
    record = db.get(Attendance, attendance_id)

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attendance record not found",
        )

    changes = payload.model_dump(exclude_unset=True)
    correction_note = changes.pop("correction_note").strip()

    if not correction_note:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Correction reason cannot be empty",
        )

    if not changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least one attendance field to correct",
        )

    old_check_in = record.check_in
    old_check_out = record.check_out

    new_check_in = changes.get("check_in", old_check_in)
    new_check_out = changes.get("check_out", old_check_out)

    if new_check_in is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Check-in time cannot be empty",
        )

    if new_check_out is not None and new_check_out < new_check_in:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Check-out must be after check-in",
        )

    for field, value in changes.items():
        setattr(record, field, value)

    if "check_in" in changes or "check_out" in changes:
        if record.check_out is None:
            record.working_minutes = None
        else:
            record.working_minutes = int(
                (
                    record.check_out - record.check_in
                ).total_seconds() // 60
            )

    record.correction_note = correction_note
    record.corrected_by_user_id = admin_user.id

    try:
        db.commit()
        db.refresh(record)
        return record
    except Exception:
        db.rollback()
        raise
