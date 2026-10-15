
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.attendance import Attendance
from app.models.employee import Employee
from app.models.user import User
from app.schemas.shift import (
    ShiftAttendanceReport,
    ShiftAttendanceReportRow,
)
from app.services.shift_service import resolve_employee_shift


COMPANY_TIMEZONE = ZoneInfo("Asia/Kolkata")


def _localize(value: datetime) -> datetime:
    """Interpret naive timestamps as company local time."""
    if value.tzinfo is None:
        return value.replace(tzinfo=COMPANY_TIMEZONE)

    return value.astimezone(COMPANY_TIMEZONE)


def _scheduled_times(
    attendance_date: date,
    start_time: time | None,
    end_time: time | None,
) -> tuple[datetime | None, datetime | None]:
    """Build scheduled timestamps, including overnight shifts."""
    if start_time is None or end_time is None:
        return None, None

    scheduled_start = datetime.combine(
        attendance_date,
        start_time,
        tzinfo=COMPANY_TIMEZONE,
    )

    scheduled_end_date = attendance_date

    # A night shift ending at or before its start crosses midnight.
    if end_time <= start_time:
        scheduled_end_date += timedelta(days=1)

    scheduled_end = datetime.combine(
        scheduled_end_date,
        end_time,
        tzinfo=COMPANY_TIMEZONE,
    )

    return scheduled_start, scheduled_end


def _minutes_between(
    later: datetime,
    earlier: datetime,
) -> int:
    return max(
        0,
        int((later - earlier).total_seconds() // 60),
    )


def get_shift_attendance_report(
    db: Session,
    start_date: date,
    end_date: date,
    employee_id: int | None = None,
    department_id: int | None = None,
    skip: int = 0,
    limit: int = 200,
) -> ShiftAttendanceReport:
    """
    Generate an attendance report enriched with applicable shifts.

    Employee-specific assignments take priority over department
    assignments. Admin attendance corrections are reflected because
    the report uses the saved check-in and check-out timestamps.
    """
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="start_date cannot be after end_date",
        )

    if (end_date - start_date).days > 366:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Report date range cannot exceed 367 calendar days",
        )

    if skip < 0 or limit < 1 or limit > 500:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="skip must be nonnegative and limit must be 1-500",
        )

    if employee_id is not None and department_id is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Filter by employee or department, not both",
        )

    statement = (
        select(Attendance)
        .join(Employee, Attendance.employee_id == Employee.id)
        .join(User, Employee.user_id == User.id)
        .options(
            selectinload(Attendance.employee)
            .selectinload(Employee.user)
        )
        .where(
            Attendance.attendance_date >= start_date,
            Attendance.attendance_date <= end_date,
        )
    )

    if employee_id is not None:
        statement = statement.where(
            Attendance.employee_id == employee_id
        )

    if department_id is not None:
        statement = statement.where(
            Employee.department_id == department_id
        )

    statement = (
        statement
        .order_by(
            Attendance.attendance_date,
            Attendance.employee_id,
        )
        .offset(skip)
        .limit(limit)
    )

    attendance_records = list(db.scalars(statement).all())

    report_rows: list[ShiftAttendanceReportRow] = []

    for record in attendance_records:
        employee = record.employee
        user = employee.user

        employee_name = (
            f"{user.first_name} {user.last_name}"
        ).strip()

        assignment_result = resolve_employee_shift(
            db,
            employee.id,
            record.attendance_date,
        )

        shift = (
            assignment_result[1]
            if assignment_result is not None
            else None
        )

        scheduled_start = None
        scheduled_end = None

        late_minutes = 0
        early_checkout_minutes = 0
        overtime_minutes = 0

        if shift is not None:
            scheduled_start, scheduled_end = _scheduled_times(
                record.attendance_date,
                shift.start_time,
                shift.end_time,
            )

            check_in = (
                _localize(record.check_in)
                if record.check_in is not None
                else None
            )

            check_out = (
                _localize(record.check_out)
                if record.check_out is not None
                else None
            )

            # A check-in is late only after the configured grace period.
            if (
                check_in is not None
                and scheduled_start is not None
            ):
                elapsed_late = _minutes_between(
                    check_in,
                    scheduled_start,
                )

                late_minutes = max(
                    0,
                    elapsed_late - shift.grace_minutes,
                )

            # Early checkout uses the scheduled end timestamp.
            if (
                check_out is not None
                and scheduled_end is not None
            ):
                early_checkout_minutes = _minutes_between(
                    scheduled_end,
                    check_out,
                )

            # Existing working_minutes records elapsed check-in/out
            # minutes, so subtract the configured break to estimate
            # net worked minutes before calculating overtime.
            if record.working_minutes is not None:
                net_worked_minutes = max(
                    0,
                    record.working_minutes - shift.break_minutes,
                )

                overtime_minutes = max(
                    0,
                    net_worked_minutes
                    - shift.expected_work_minutes,
                )

        report_rows.append(
            ShiftAttendanceReportRow(
                attendance_id=record.id,
                employee_id=employee.id,
                employee_code=employee.employee_code,
                employee_name=employee_name,
                attendance_date=record.attendance_date,
                shift_id=shift.id if shift else None,
                shift_name=shift.name if shift else None,
                shift_type=shift.shift_type if shift else None,
                scheduled_start_at=scheduled_start,
                scheduled_end_at=scheduled_end,
                check_in=record.check_in,
                check_out=record.check_out,
                late_minutes=late_minutes,
                early_checkout_minutes=early_checkout_minutes,
                overtime_minutes=overtime_minutes,
                is_overridden=bool(
                    record.corrected_by_user_id is not None
                ),
            )
        )

    return ShiftAttendanceReport(
        start_date=start_date,
        end_date=end_date,
        total_records=len(report_rows),
        late_records=sum(
            row.late_minutes > 0 for row in report_rows
        ),
        early_checkout_records=sum(
            row.early_checkout_minutes > 0
            for row in report_rows
        ),
        overtime_records=sum(
            row.overtime_minutes > 0
            for row in report_rows
        ),
        total_overtime_minutes=sum(
            row.overtime_minutes for row in report_rows
        ),
        records=report_rows,
    )
