from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LeaveTypeCreate(BaseModel):
    code: str = Field(
        min_length=2,
        max_length=30,
        pattern=r"^[A-Za-z][A-Za-z0-9_]*$",
    )
    name: str = Field(min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    is_paid: bool = True
    annual_quota: Decimal = Field(
        ge=0,
        max_digits=6,
        decimal_places=2,
    )

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Leave type name cannot be empty")
        return value


class LeaveTypeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    is_paid: bool | None = None
    annual_quota: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=6,
        decimal_places=2,
    )
    is_active: bool | None = None


class LeaveTypeRead(BaseModel):
    id: int
    code: str
    name: str
    description: str | None
    is_paid: bool
    annual_quota: Decimal
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class LeaveRequestCreate(BaseModel):
    leave_type_id: int = Field(gt=0)
    start_date: date
    end_date: date
    reason: str = Field(min_length=3, max_length=2000)

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError("Please provide a meaningful leave reason")
        return value


class LeaveRequestRead(BaseModel):
    id: int
    employee_id: int
    employee_name: str
    employee_email: str
    leave_type_id: int
    leave_type_name: str
    leave_type_code: str
    is_paid: bool
    start_date: date
    end_date: date
    total_days: Decimal
    reason: str
    status: str
    approved_by_user_id: int | None
    decided_at: datetime | None
    decision_note: str | None
    created_at: datetime


class LeaveDecision(BaseModel):
    decision_note: str | None = Field(default=None, max_length=2000)


class LeaveBalanceRead(BaseModel):
    employee_id: int
    leave_type_id: int
    leave_type_name: str
    leave_type_code: str
    year: int
    entitled_days: Decimal
    used_days: Decimal
    available_days: Decimal
    is_paid: bool


class LeaveYearSummary(BaseModel):
    year: int
    total_requests: int
    approved_requests: int
    pending_requests: int
    rejected_requests: int


LeaveRequestStatus = Literal["PENDING", "APPROVED", "REJECTED", "CANCELLED"]