
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class PayrollGenerateRequest(BaseModel):
    year: int = Field(ge=2000, le=2100)
    month: int = Field(ge=1, le=12)


class PayrollRunRead(BaseModel):
    id: int
    year: int
    month: int
    period_start: date
    period_end: date
    status: str
    generated_by_user_id: int
    locked_by_user_id: int | None
    generated_at: datetime
    locked_at: datetime | None

    record_count: int
    total_gross_salary: Decimal
    total_lop_deduction: Decimal
    total_deductions: Decimal
    total_net_salary: Decimal


class PayrollRecordRead(BaseModel):
    id: int
    payroll_run_id: int
    employee_id: int
    employee_code: str
    employee_name: str
    employee_email: str

    year: int
    month: int
    monthly_salary: Decimal
    eligible_working_days: int
    present_days: Decimal
    paid_leave_days: Decimal
    payable_days: Decimal
    lop_days: Decimal

    base_pay: Decimal
    lop_deduction: Decimal
    other_earnings: Decimal
    other_deductions: Decimal
    gross_salary: Decimal
    net_salary: Decimal

    credit_status: str
    simulated_credit_at: datetime | None
    created_at: datetime


class PayrollAdjustmentCreate(BaseModel):
    employee_id: int = Field(gt=0)
    adjustment_type: Literal["EARNING", "DEDUCTION"]
    amount: Decimal = Field(
        gt=0,
        max_digits=12,
        decimal_places=2,
    )
    description: str = Field(min_length=3, max_length=1000)


class PayrollAdjustmentRead(BaseModel):
    id: int
    payroll_record_id: int
    created_by_user_id: int
    adjustment_type: str
    amount: Decimal
    description: str
    created_at: datetime
