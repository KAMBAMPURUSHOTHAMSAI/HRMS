
from datetime import date, datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


HolidayType = Literal["COMPANY", "REGIONAL", "OPTIONAL"]


class HolidayCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    holiday_date: date
    holiday_type: HolidayType
    region: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Holiday name must contain at least 2 characters")
        return value

    @field_validator("region")
    @classmethod
    def normalize_region(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @model_validator(mode="after")
    def validate_region(self):
        if self.holiday_type == "REGIONAL" and not self.region:
            raise ValueError("Region is required for regional holidays")
        if self.holiday_type != "REGIONAL" and self.region:
            raise ValueError(
                "Region must only be provided for regional holidays"
            )
        return self


class HolidayUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    holiday_date: date | None = None
    holiday_type: HolidayType | None = None
    region: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Holiday name must contain at least 2 characters")
        return value

    @field_validator("region")
    @classmethod
    def normalize_region(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @model_validator(mode="after")
    def validate_region(self):
        if self.holiday_type == "REGIONAL" and not self.region:
            raise ValueError(
                "Provide the region when changing a holiday to REGIONAL"
            )
        if (
            self.holiday_type is not None
            and self.holiday_type != "REGIONAL"
            and self.region
        ):
            raise ValueError(
                "Region must only be provided for regional holidays"
            )
        return self


class HolidayRead(BaseModel):
    id: int
    name: str
    holiday_date: date
    holiday_type: HolidayType
    region: str | None
    description: str | None
    is_active: bool
    created_by_user_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HolidaySelectionRead(BaseModel):
    id: int
    employee_id: int
    holiday_id: int
    status: Literal["SELECTED", "CANCELLED"]
    selected_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
