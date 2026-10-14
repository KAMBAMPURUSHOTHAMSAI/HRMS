
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.permissions import require_permissions
from app.schemas.audit_log import AuditLogRead
from app.services.audit_service import (
    get_audit_log,
    list_audit_logs,
)


router = APIRouter(
    prefix="/audit-logs",
    tags=["Audit Logs"],
)


@router.get(
    "",
    response_model=list[AuditLogRead],
)
def read_audit_logs(
    actor_user_id: int | None = Query(default=None, gt=0),
    action: str | None = Query(default=None, max_length=100),
    entity_type: str | None = Query(default=None, max_length=100),
    entity_id: str | None = Query(default=None, max_length=100),
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _user=Depends(require_permissions("AUDIT_LOGS.READ")),
):
    return list_audit_logs(
        db,
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{log_id}",
    response_model=AuditLogRead,
)
def read_audit_log(
    log_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_permissions("AUDIT_LOGS.READ")),
):
    return get_audit_log(db, log_id)
