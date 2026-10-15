
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EmployeeSalaryComponentCreate(BaseModel):
    employee_id: int = Field(gt=0)
    component_id: int = Field(gt=0)

    amount_override: Decimal | None = Field(default=None, ge=0)

    effective_from: date
    effective_to: date | None = None

    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_effective_dates(self):
        if (
            self.effective_to is not None
            and self.effective_to < self.effective_from
        ):
            raise ValueError(
                "effective_to cannot be earlier than effective_from"
            )
        return self


class EmployeeSalaryComponentUpdate(BaseModel):
    amount_override: Decimal | None = Field(default=None, ge=0)
    effective_from: date | None = None
    effective_to: date | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_effective_dates(self):
        if (
            self.effective_from is not None
            and self.effective_to is not None
            and self.effective_to < self.effective_from
        ):
            raise ValueError(
                "effective_to cannot be earlier than effective_from"
            )
        return self


class EmployeeSalaryComponentRead(BaseModel):
    id: int
    employee_id: int
    component_id: int

    amount_override: Decimal | None = None

    effective_from: date
    effective_to: date | None = None

    notes: str | None = None
    assigned_by_user_id: int | None = None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
