from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AttendanceRead(BaseModel):
    id: int
    employee_id: int
    attendance_date: date
    check_in: datetime
    check_out: datetime | None
    working_minutes: int | None
    status: str
    correction_note: str | None
    corrected_by_user_id: int | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AttendanceCorrection(BaseModel):
    check_in: datetime | None = None
    check_out: datetime | None = None
    status: Literal["PRESENT", "HALF_DAY"] | None = None
    correction_note: str = Field(min_length=3, max_length=1000)

    @field_validator("check_in", "check_out")
    @classmethod
    def require_timezone(cls, value: datetime | None):
        if value is not None and (
            value.tzinfo is None or value.utcoffset() is None
        ):
            raise ValueError("Datetime must include a timezone")
        return value


class AttendanceSummary(BaseModel):
    year: int
    month: int
    days_recorded: int
    total_worked_minutes: int
    total_worked_hours: Decimal

    # Actual monthly attendance counts
    present_days: int = 0
    half_days: int = 0