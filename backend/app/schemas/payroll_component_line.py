
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


PayrollComponentType = Literal["EARNING", "DEDUCTION"]


class PayrollComponentLineCreate(BaseModel):
    payroll_record_id: int = Field(gt=0)
    salary_component_id: int | None = Field(default=None, gt=0)

    component_code: str = Field(min_length=1, max_length=50)
    component_name: str = Field(min_length=1, max_length=150)
    component_type: PayrollComponentType

    amount: Decimal = Field(ge=0)
    is_taxable: bool = False
    calculation_details: str | None = None

    @field_validator("component_code", "component_name")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be empty")
        return value


class PayrollComponentLineRead(BaseModel):
    id: int
    payroll_record_id: int
    salary_component_id: int | None = None

    component_code: str
    component_name: str
    component_type: PayrollComponentType

    amount: Decimal
    is_taxable: bool
    calculation_details: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
