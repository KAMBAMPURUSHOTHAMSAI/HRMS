
from datetime import datetime
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class NotificationRead(BaseModel):
    id: int
    user_id: int
    event_type: str
    title: str
    message: str
    is_read: bool
    read_at: datetime | None
    extra_data: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UnreadNotificationCount(BaseModel):
    unread_count: int


class MarkReadResponse(BaseModel):
    message: str
    updated_count: int


class EmailDeliveryLogRead(BaseModel):
    id: int
    user_id: int | None
    recipient_email: str
    event_type: str
    subject: str
    template_name: str
    status: str
    attempt_count: int
    error_message: str | None
    last_attempt_at: datetime | None
    sent_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationPreferenceRead(BaseModel):
    id: int
    user_id: int
    in_app_enabled: bool
    leave_updates_enabled: bool
    payroll_updates_enabled: bool
    attendance_alerts_enabled: bool
    announcements_enabled: bool
    other_updates_enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationPreferenceUpdate(BaseModel):
    in_app_enabled: bool | None = None
    leave_updates_enabled: bool | None = None
    payroll_updates_enabled: bool | None = None
    attendance_alerts_enabled: bool | None = None
    announcements_enabled: bool | None = None
    other_updates_enabled: bool | None = None


class NotificationBroadcastCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    message: str = Field(min_length=2, max_length=5000)

    scope: Literal["ALL", "DEPARTMENTS"] = "ALL"

    department_ids: list[int] = Field(
        default_factory=list,
        max_length=100,
    )

    @field_validator("title", "message")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("This field cannot be empty")

        return value

    @field_validator("department_ids")
    @classmethod
    def validate_department_ids(cls, values: list[int]) -> list[int]:
        if any(department_id <= 0 for department_id in values):
            raise ValueError("Department IDs must be positive integers")

        # Remove duplicate department IDs without changing order.
        return list(dict.fromkeys(values))

    @model_validator(mode="after")
    def validate_scope(self):
        if self.scope == "DEPARTMENTS" and not self.department_ids:
            raise ValueError(
                "Select at least one department for a department broadcast"
            )

        if self.scope == "ALL" and self.department_ids:
            raise ValueError(
                "department_ids must be empty for an organization-wide broadcast"
            )

        return self


class NotificationBroadcastResponse(BaseModel):
    message: str
    scope: Literal["ALL", "DEPARTMENTS"]
    target_count: int
    notifications_created: int
    skipped_by_preferences: int
