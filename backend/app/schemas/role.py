
import re

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class RoleCreate(BaseModel):
    name: str = Field(min_length=2, max_length=30)
    description: str | None = Field(default=None, max_length=250)

    model_config = ConfigDict(extra="forbid")

    @field_validator("name")
    @classmethod
    def normalize_role_name(cls, value: str) -> str:
        value = value.strip().upper().replace(" ", "_")

        if not re.fullmatch(r"[A-Z][A-Z0-9_-]{1,29}", value):
            raise ValueError(
                "Role name must start with a letter and contain "
                "only letters, numbers, underscores or hyphens."
            )

        return value

    @field_validator("description")
    @classmethod
    def normalize_role_description(cls, value):
        return value.strip() or None if value is not None else None


class RoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=30)
    description: str | None = Field(default=None, max_length=250)
    is_active: bool | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("name")
    @classmethod
    def normalize_role_name(cls, value):
        if value is None:
            return None

        value = value.strip().upper().replace(" ", "_")

        if not re.fullmatch(r"[A-Z][A-Z0-9_-]{1,29}", value):
            raise ValueError("Invalid role name format.")

        return value

    @field_validator("description")
    @classmethod
    def normalize_role_description(cls, value):
        return value.strip() or None if value is not None else None

    @model_validator(mode="after")
    def require_update_field(self):
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update.")

        return self


class PermissionCreate(BaseModel):
    code: str = Field(min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=250)

    model_config = ConfigDict(extra="forbid")

    @field_validator("code")
    @classmethod
    def normalize_permission_code(cls, value: str) -> str:
        value = value.strip().upper().replace(" ", "_")

        if not re.fullmatch(r"[A-Z][A-Z0-9_.:-]{1,99}", value):
            raise ValueError("Invalid permission code format.")

        return value

    @field_validator("description")
    @classmethod
    def normalize_permission_description(cls, value):
        return value.strip() or None if value is not None else None


class PermissionUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=250)

    model_config = ConfigDict(extra="forbid")

    @field_validator("code")
    @classmethod
    def normalize_permission_code(cls, value):
        if value is None:
            return None

        value = value.strip().upper().replace(" ", "_")

        if not re.fullmatch(r"[A-Z][A-Z0-9_.:-]{1,99}", value):
            raise ValueError("Invalid permission code format.")

        return value

    @field_validator("description")
    @classmethod
    def normalize_permission_description(cls, value):
        return value.strip() or None if value is not None else None

    @model_validator(mode="after")
    def require_update_field(self):
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update.")

        return self


class PermissionRead(BaseModel):
    id: int
    code: str
    description: str | None

    model_config = ConfigDict(from_attributes=True)


class RoleRead(BaseModel):
    id: int
    name: str
    description: str | None
    is_active: bool
    permission_ids: list[int] = Field(default_factory=list)
    user_ids: list[int] = Field(default_factory=list)
    user_count: int = 0
