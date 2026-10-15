
from datetime import date, datetime, time
from decimal import Decimal
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


ShiftType = Literal["GENERAL", "NIGHT", "FLEXIBLE", "REMOTE"]


class ShiftCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    shift_type: ShiftType = "GENERAL"

    start_time: time | None = None
    end_time: time | None = None

    break_minutes: int = Field(default=60, ge=0, le=720)
    grace_minutes: int = Field(default=10, ge=0, le=240)

    expected_work_minutes: int = Field(
        default=480,
        gt=0,
        le=1440,
    )

    overtime_multiplier: Decimal = Field(
        default=Decimal("1.50"),
        ge=Decimal("1.00"),
        le=Decimal("10.00"),
        max_digits=4,
        decimal_places=2,
    )

    is_active: bool = True

    @model_validator(mode="after")
    def validate_shift_times(self):
        if self.shift_type in ("GENERAL", "NIGHT"):
            if self.start_time is None or self.end_time is None:
                raise ValueError(
                    "Start and end times are required for GENERAL and NIGHT shifts"
                )

            if (
                self.shift_type == "GENERAL"
                and self.end_time <= self.start_time
            ):
                raise ValueError(
                    "GENERAL shift end time must be after start time"
                )

            if self.start_time == self.end_time:
                raise ValueError(
                    "Shift start and end times cannot be identical"
                )

        return self


class ShiftUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
    )

    shift_type: ShiftType | None = None

    start_time: time | None = None
    end_time: time | None = None

    break_minutes: int | None = Field(
        default=None,
        ge=0,
        le=720,
    )

    grace_minutes: int | None = Field(
        default=None,
        ge=0,
        le=240,
    )

    expected_work_minutes: int | None = Field(
        default=None,
        gt=0,
        le=1440,
    )

    overtime_multiplier: Decimal | None = Field(
        default=None,
        ge=Decimal("1.00"),
        le=Decimal("10.00"),
        max_digits=4,
        decimal_places=2,
    )

    is_active: bool | None = None


class ShiftRead(BaseModel):
    id: int
    name: str
    shift_type: ShiftType
    start_time: time | None
    end_time: time | None
    break_minutes: int
    grace_minutes: int
    expected_work_minutes: int
    overtime_multiplier: Decimal
    is_active: bool
    created_by_user_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ShiftAssignmentCreate(BaseModel):
    shift_id: int

    employee_id: int | None = None
    department_id: int | None = None

    effective_from: date
    effective_to: date | None = None

    @model_validator(mode="after")
    def validate_assignment(self):
        has_employee = self.employee_id is not None
        has_department = self.department_id is not None

        if has_employee == has_department:
            raise ValueError(
                "Provide exactly one of employee_id or department_id"
            )

        if self.shift_id <= 0:
            raise ValueError("shift_id must be positive")

        if self.employee_id is not None and self.employee_id <= 0:
            raise ValueError("employee_id must be positive")

        if self.department_id is not None and self.department_id <= 0:
            raise ValueError("department_id must be positive")

        if (
            self.effective_to is not None
            and self.effective_to < self.effective_from
        ):
            raise ValueError(
                "effective_to cannot be before effective_from"
            )

        return self


class ShiftAssignmentRead(BaseModel):
    id: int
    shift_id: int
    employee_id: int | None
    department_id: int | None
    effective_from: date
    effective_to: date | None
    assigned_by_user_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ShiftAttendanceReportRow(BaseModel):
    attendance_id: int
    employee_id: int
    employee_code: str
    employee_name: str

    attendance_date: date

    shift_id: int | None
    shift_name: str | None
    shift_type: ShiftType | None

    scheduled_start_at: datetime | None
    scheduled_end_at: datetime | None

    check_in: datetime | None
    check_out: datetime | None

    late_minutes: int = Field(default=0, ge=0)
    early_checkout_minutes: int = Field(default=0, ge=0)
    overtime_minutes: int = Field(default=0, ge=0)

    is_overridden: bool = False


class ShiftAttendanceReport(BaseModel):
    start_date: date
    end_date: date

    total_records: int = Field(default=0, ge=0)
    late_records: int = Field(default=0, ge=0)
    early_checkout_records: int = Field(default=0, ge=0)
    overtime_records: int = Field(default=0, ge=0)

    total_overtime_minutes: int = Field(default=0, ge=0)

    records: list[ShiftAttendanceReportRow] = Field(
        default_factory=list
    )
