
from datetime import datetime
from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.user import User


def record_audit_event(
    db: Session,
    *,
    action: str,
    entity_type: str,
    description: str,
    actor: User | None = None,
    entity_id: str | int | None = None,
    details: dict[str, Any] | None = None,
    request: Request | None = None,
    actor_roles: list[str] | None = None,
) -> AuditLog:
    """
    Add an audit event to the current transaction.

    Call this before the business transaction commits so that
    the business change and its audit event can commit together.
    This function intentionally does not commit the transaction.
    """

    normalized_action = action.strip().upper()
    normalized_entity = entity_type.strip()

    if not normalized_action or not normalized_entity:
        raise ValueError("Action and entity type are required")

    if not description.strip():
        raise ValueError("Audit description cannot be empty")

    roles = actor_roles

    if roles is None and actor is not None:
        roles = [
            assignment.role.name
            for assignment in actor.user_roles
            if assignment.role is not None
            and assignment.role.is_active
        ]

    client_ip = None
    user_agent = None

    if request is not None:
        if request.client is not None:
            client_ip = request.client.host

        user_agent = request.headers.get("user-agent")

    safe_details = jsonable_encoder(details or {})

    if not isinstance(safe_details, dict):
        raise ValueError("Audit details must be a JSON object")

    entry = AuditLog(
        actor_user_id=actor.id if actor else None,
        actor_email=actor.email if actor else None,
        actor_roles=",".join(sorted(set(roles or []))) or None,
        action=normalized_action,
        entity_type=normalized_entity,
        entity_id=(
            str(entity_id)
            if entity_id is not None
            else None
        ),
        description=description.strip(),
        details=safe_details,
        ip_address=client_ip,
        user_agent=user_agent[:500] if user_agent else None,
    )

    db.add(entry)
    db.flush()

    return entry


def list_audit_logs(
    db: Session,
    *,
    actor_user_id: int | None = None,
    action: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[AuditLog]:
    if (
        start_date is not None
        and end_date is not None
        and start_date > end_date
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="start_date cannot be after end_date",
        )

    statement = select(AuditLog)

    if actor_user_id is not None:
        statement = statement.where(
            AuditLog.actor_user_id == actor_user_id
        )

    if action:
        statement = statement.where(
            AuditLog.action == action.strip().upper()
        )

    if entity_type:
        statement = statement.where(
            AuditLog.entity_type == entity_type.strip()
        )

    if entity_id:
        statement = statement.where(
            AuditLog.entity_id == entity_id.strip()
        )

    if start_date is not None:
        statement = statement.where(
            AuditLog.created_at >= start_date
        )

    if end_date is not None:
        statement = statement.where(
            AuditLog.created_at <= end_date
        )

    statement = (
        statement
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset(skip)
        .limit(limit)
    )

    return list(db.scalars(statement).all())


def get_audit_log(
    db: Session,
    log_id: int,
) -> AuditLog:
    entry = db.get(AuditLog, log_id)

    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log not found",
        )

    return entry
