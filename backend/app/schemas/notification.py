
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


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
