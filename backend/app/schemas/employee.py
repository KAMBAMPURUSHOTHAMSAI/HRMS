
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class EmployeeCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)

    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)

    employee_code: str = Field(
        min_length=2,
        max_length=30,
        pattern=r"^[A-Za-z0-9_-]+$",
    )

    phone: str | None = Field(default=None, max_length=20)
    department_id: int = Field(gt=0)
    designation_id: int = Field(gt=0)
    joining_date: date
    monthly_salary: Decimal = Field(
        gt=0,
        max_digits=12,
        decimal_places=2,
    )

    @field_validator("first_name", "last_name", "employee_code")
    @classmethod
    def strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be empty")
        return value


class EmployeeUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=20)
    department_id: int | None = Field(default=None, gt=0)
    designation_id: int | None = Field(default=None, gt=0)
    joining_date: date | None = None
    monthly_salary: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=12,
        decimal_places=2,
    )

class EmployeeSelfUpdate(BaseModel):
    """Fields an employee is allowed to update in their own profile."""

    first_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    last_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    phone: str | None = Field(
        default=None,
        max_length=20,
    )

class EmployeeRead(BaseModel):
    id: int
    user_id: int
    employee_code: str

    email: EmailStr
    first_name: str
    last_name: str
    phone: str | None

    department_id: int
    department_name: str

    designation_id: int
    designation_name: str

    joining_date: date
    monthly_salary: Decimal
    employment_status: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
