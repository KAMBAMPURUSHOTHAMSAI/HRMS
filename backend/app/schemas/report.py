
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class AttendanceReportRow(BaseModel):
    id: int
    employee_id: int
    employee_code: str
    employee_name: str
    department: str
    attendance_date: date
    check_in: datetime
    check_out: datetime | None
    working_minutes: int | None
    status: str


class LeaveReportRow(BaseModel):
    id: int
    employee_id: int
    employee_code: str
    employee_name: str
    department: str
    leave_type: str
    start_date: date
    end_date: date
    total_days: Decimal
    status: str
    reason: str
    created_at: datetime


class PayrollReportRow(BaseModel):
    id: int
    employee_id: int
    employee_code: str
    employee_name: str
    department: str
    year: int
    month: int
    gross_salary: Decimal
    lop_deduction: Decimal
    other_deductions: Decimal
    net_salary: Decimal
    credit_status: str


class DashboardSummary(BaseModel):
    active_employees: int
    today_attendance_records: int
    pending_leave_requests: int
    current_month_net_payroll: Decimal
