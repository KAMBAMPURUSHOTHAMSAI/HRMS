
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.attendance import Attendance
from app.models.department import Department
from app.models.employee import Employee
from app.models.leave_request import LeaveRequest
from app.models.leave_type import LeaveType
from app.models.payroll_record import PayrollRecord
from app.models.payroll_run import PayrollRun
from app.models.user import User
from app.utils.csv_export import export_csv_bytes
from app.utils.pdf_utils import export_pdf_bytes


COMPANY_TIMEZONE = ZoneInfo("Asia/Kolkata")


ATTENDANCE_COLUMNS = [
    ("id", "Attendance ID"),
    ("employee_code", "Employee Code"),
    ("employee_name", "Employee"),
    ("department", "Department"),
    ("attendance_date", "Date"),
    ("check_in", "Check In"),
    ("check_out", "Check Out"),
    ("working_minutes", "Working Minutes"),
    ("status", "Status"),
]

LEAVE_COLUMNS = [
    ("id", "Leave Request ID"),
    ("employee_code", "Employee Code"),
    ("employee_name", "Employee"),
    ("department", "Department"),
    ("leave_type", "Leave Type"),
    ("start_date", "Start Date"),
    ("end_date", "End Date"),
    ("total_days", "Days"),
    ("status", "Status"),
    ("reason", "Reason"),
    ("created_at", "Applied At"),
]

PAYROLL_COLUMNS = [
    ("id", "Payroll Record ID"),
    ("employee_code", "Employee Code"),
    ("employee_name", "Employee"),
    ("department", "Department"),
    ("year", "Year"),
    ("month", "Month"),
    ("gross_salary", "Gross Salary"),
    ("lop_deduction", "LOP Deduction"),
    ("other_deductions", "Other Deductions"),
    ("net_salary", "Net Salary"),
    ("credit_status", "Credit Status"),
]


def _validate_dates(
    start_date: date | None,
    end_date: date | None,
) -> None:
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="start_date cannot be after end_date",
        )


def get_attendance_report(
    db: Session,
    start_date: date | None = None,
    end_date: date | None = None,
    department_id: int | None = None,
    employee_id: int | None = None,
    skip: int = 0,
    limit: int = 500,
) -> list[dict]:
    _validate_dates(start_date, end_date)

    statement = (
        select(
            Attendance.id.label("id"),
            Employee.id.label("employee_id"),
            Employee.employee_code.label("employee_code"),
            func.concat(
                User.first_name,
                " ",
                User.last_name,
            ).label("employee_name"),
            Department.name.label("department"),
            Attendance.attendance_date.label("attendance_date"),
            Attendance.check_in.label("check_in"),
            Attendance.check_out.label("check_out"),
            Attendance.working_minutes.label("working_minutes"),
            Attendance.status.label("status"),
        )
        .join(Employee, Attendance.employee_id == Employee.id)
        .join(User, Employee.user_id == User.id)
        .join(
            Department,
            Employee.department_id == Department.id,
        )
    )

    if start_date is not None:
        statement = statement.where(
            Attendance.attendance_date >= start_date
        )

    if end_date is not None:
        statement = statement.where(
            Attendance.attendance_date <= end_date
        )

    if department_id is not None:
        statement = statement.where(
            Employee.department_id == department_id
        )

    if employee_id is not None:
        statement = statement.where(
            Employee.id == employee_id
        )

    statement = (
        statement
        .order_by(
            Attendance.attendance_date.desc(),
            Employee.employee_code,
        )
        .offset(skip)
        .limit(limit)
    )

    rows = db.execute(statement).mappings().all()

    return [dict(row) for row in rows]


def get_leave_report(
    db: Session,
    start_date: date | None = None,
    end_date: date | None = None,
    department_id: int | None = None,
    leave_status: str | None = None,
    skip: int = 0,
    limit: int = 500,
) -> list[dict]:
    _validate_dates(start_date, end_date)

    # Join LeaveType directly to avoid an additional query per row.
    statement = (
        select(
            LeaveRequest.id.label("id"),
            Employee.id.label("employee_id"),
            Employee.employee_code.label("employee_code"),
            func.concat(
                User.first_name,
                " ",
                User.last_name,
            ).label("employee_name"),
            Department.name.label("department"),
            LeaveType.name.label("leave_type"),
            LeaveRequest.start_date.label("start_date"),
            LeaveRequest.end_date.label("end_date"),
            LeaveRequest.total_days.label("total_days"),
            LeaveRequest.status.label("status"),
            LeaveRequest.reason.label("reason"),
            LeaveRequest.created_at.label("created_at"),
        )
        .join(
            Employee,
            LeaveRequest.employee_id == Employee.id,
        )
        .join(User, Employee.user_id == User.id)
        .join(
            Department,
            Employee.department_id == Department.id,
        )
        .join(
            LeaveType,
            LeaveRequest.leave_type_id == LeaveType.id,
        )
    )

    if start_date is not None:
        statement = statement.where(
            LeaveRequest.end_date >= start_date
        )

    if end_date is not None:
        statement = statement.where(
            LeaveRequest.start_date <= end_date
        )

    if department_id is not None:
        statement = statement.where(
            Employee.department_id == department_id
        )

    if leave_status is not None:
        statement = statement.where(
            LeaveRequest.status == leave_status
        )

    statement = (
        statement
        .order_by(LeaveRequest.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    rows = db.execute(statement).mappings().all()

    return [dict(row) for row in rows]


def get_payroll_report(
    db: Session,
    year: int | None = None,
    month: int | None = None,
    department_id: int | None = None,
    skip: int = 0,
    limit: int = 500,
) -> list[dict]:
    if month is not None and not 1 <= month <= 12:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="month must be between 1 and 12",
        )

    if year is None and month is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide year when filtering by month",
        )

    statement = (
        select(
            PayrollRecord.id.label("id"),
            Employee.id.label("employee_id"),
            Employee.employee_code.label("employee_code"),
            func.concat(
                User.first_name,
                " ",
                User.last_name,
            ).label("employee_name"),
            Department.name.label("department"),
            PayrollRun.year.label("year"),
            PayrollRun.month.label("month"),
            PayrollRecord.gross_salary.label("gross_salary"),
            PayrollRecord.lop_deduction.label("lop_deduction"),
            PayrollRecord.other_deductions.label("other_deductions"),
            PayrollRecord.net_salary.label("net_salary"),
            PayrollRecord.credit_status.label("credit_status"),
        )
        .join(
            PayrollRun,
            PayrollRecord.payroll_run_id == PayrollRun.id,
        )
        .join(Employee, PayrollRecord.employee_id == Employee.id)
        .join(User, Employee.user_id == User.id)
        .join(
            Department,
            Employee.department_id == Department.id,
        )
    )

    if year is not None:
        statement = statement.where(
            PayrollRun.year == year
        )

    if month is not None:
        statement = statement.where(
            PayrollRun.month == month
        )

    if department_id is not None:
        statement = statement.where(
            Employee.department_id == department_id
        )

    statement = (
        statement
        .order_by(
            PayrollRun.year.desc(),
            PayrollRun.month.desc(),
            Employee.employee_code,
        )
        .offset(skip)
        .limit(limit)
    )

    rows = db.execute(statement).mappings().all()

    return [dict(row) for row in rows]


def get_dashboard_summary(db: Session) -> dict:
    today = datetime.now(COMPANY_TIMEZONE).date()

    active_employees = db.scalar(
        select(func.count(Employee.id))
        .join(User, Employee.user_id == User.id)
        .where(
            Employee.employment_status == "ACTIVE",
            User.is_active.is_(True),
        )
    ) or 0

    attendance_today = db.scalar(
        select(func.count(Attendance.id)).where(
            Attendance.attendance_date == today
        )
    ) or 0

    pending_leaves = db.scalar(
        select(func.count(LeaveRequest.id)).where(
            LeaveRequest.status == "PENDING"
        )
    ) or 0

    current_month_payroll = db.scalar(
        select(
            func.coalesce(
                func.sum(PayrollRecord.net_salary),
                0,
            )
        )
        .join(
            PayrollRun,
            PayrollRecord.payroll_run_id == PayrollRun.id,
        )
        .where(
            PayrollRun.year == today.year,
            PayrollRun.month == today.month,
        )
    ) or Decimal("0.00")

    return {
        "active_employees": int(active_employees),
        "today_attendance_records": int(attendance_today),
        "pending_leave_requests": int(pending_leaves),
        "current_month_net_payroll": Decimal(
            str(current_month_payroll)
        ),
    }


def export_report(
    report_type: str,
    file_format: str,
    rows: list[dict],
) -> tuple[bytes, str, str]:
    columns_map = {
        "attendance": ATTENDANCE_COLUMNS,
        "leaves": LEAVE_COLUMNS,
        "payroll": PAYROLL_COLUMNS,
    }

    titles = {
        "attendance": "HRMS Attendance Report",
        "leaves": "HRMS Leave Report",
        "payroll": "HRMS Payroll Report",
    }

    if report_type not in columns_map:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unsupported report type",
        )

    columns = columns_map[report_type]
    title = titles[report_type]

    if file_format == "csv":
        return (
            export_csv_bytes(rows, columns),
            "text/csv; charset=utf-8",
            f"{report_type}_report.csv",
        )

    if file_format == "pdf":
        return (
            export_pdf_bytes(title, rows, columns),
            "application/pdf",
            f"{report_type}_report.pdf",
        )

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Export format must be csv or pdf",
    )
