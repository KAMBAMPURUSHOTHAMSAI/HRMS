
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class UserUpdate(BaseModel):
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
    is_active: bool | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("first_name", "last_name", mode="before")
    @classmethod
    def normalize_name(cls, value):
        if value is None:
            return None

        if isinstance(value, str):
            value = value.strip()

            if not value:
                raise ValueError("Name cannot be empty.")

        return value

    @model_validator(mode="after")
    def require_update_field(self):
        if (
            self.first_name is None
            and self.last_name is None
            and self.is_active is None
        ):
            raise ValueError("Provide at least one field to update.")

        return self


class UserRead(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    is_active: bool
    roles: list[str] = Field(default_factory=list)
    employee_id: int | None = None
    employee_code: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
