
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class CompensationHistoryCreate(BaseModel):
    employee_id: int = Field(gt=0)

    previous_monthly_salary: Decimal | None = Field(
        default=None,
        ge=0,
    )
    new_monthly_salary: Decimal = Field(gt=0)

    effective_from: date
    effective_to: date | None = None

    reason: str = Field(min_length=2, max_length=500)
    notes: str | None = None

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Reason cannot be empty")
        return value

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


class CompensationHistoryRead(BaseModel):
    id: int
    employee_id: int

    previous_monthly_salary: Decimal | None = None
    new_monthly_salary: Decimal

    effective_from: date
    effective_to: date | None = None

    reason: str
    notes: str | None = None

    revised_by_user_id: int | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
