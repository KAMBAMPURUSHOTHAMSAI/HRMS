
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AuditLogRead(BaseModel):
    id: int

    actor_user_id: int | None
    actor_email: str | None
    actor_roles: str | None

    action: str
    entity_type: str
    entity_id: str | None

    description: str
    details: dict[str, Any]

    ip_address: str | None
    user_agent: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditLogFilter(BaseModel):
    action: str | None = Field(default=None, max_length=100)
    entity_type: str | None = Field(default=None, max_length=100)
    entity_id: str | None = Field(default=None, max_length=100)
    actor_user_id: int | None = Field(default=None, gt=0)
