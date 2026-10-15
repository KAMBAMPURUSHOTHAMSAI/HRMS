
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


ComponentType = Literal["EARNING", "DEDUCTION"]
CalculationType = Literal["FIXED", "PERCENTAGE"]
PercentageBase = Literal["BASE_PAY", "MONTHLY_SALARY"]


class SalaryComponentCreate(BaseModel):
    code: str = Field(min_length=2, max_length=40)
    name: str = Field(min_length=2, max_length=120)
    description: str | None = None

    component_type: ComponentType
    calculation_type: CalculationType = "FIXED"
    default_amount: Decimal = Field(default=Decimal("0.00"), ge=0)
    percentage_base: PercentageBase = "BASE_PAY"

    is_variable: bool = False
    is_taxable: bool = True
    is_active: bool = True

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        value = value.strip().upper()
        if not value:
            raise ValueError("Component code cannot be empty")
        return value

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Component name cannot be empty")
        return value


class SalaryComponentUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=2, max_length=40)
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = None

    component_type: ComponentType | None = None
    calculation_type: CalculationType | None = None
    default_amount: Decimal | None = Field(default=None, ge=0)
    percentage_base: PercentageBase | None = None

    is_variable: bool | None = None
    is_taxable: bool | None = None
    is_active: bool | None = None

    @field_validator("code")
    @classmethod
    def normalize_optional_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().upper()
        if not value:
            raise ValueError("Component code cannot be empty")
        return value

    @field_validator("name")
    @classmethod
    def normalize_optional_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Component name cannot be empty")
        return value


class SalaryComponentRead(BaseModel):
    id: int
    code: str
    name: str
    description: str | None = None

    component_type: ComponentType
    calculation_type: CalculationType
    default_amount: Decimal
    percentage_base: PercentageBase

    is_variable: bool
    is_taxable: bool
    is_active: bool

    created_by_user_id: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
