
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.permissions import require_permissions
from app.models.user import User
from app.schemas.compensation_history import (
    CompensationHistoryCreate,
    CompensationHistoryRead,
)
from app.services.compensation_history_service import (
    create_compensation_revision,
    list_compensation_history,
)


router = APIRouter(
    prefix="/compensation-history",
    tags=["Compensation History"],
)


@router.get(
    "/{employee_id}",
    response_model=list[CompensationHistoryRead],
)
def read_employee_compensation_history(
    employee_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(
        require_permissions("PAYROLL.COMPONENTS_READ")
    ),
):
    return list_compensation_history(
        db=db,
        employee_id=employee_id,
    )


@router.post(
    "",
    response_model=CompensationHistoryRead,
    status_code=status.HTTP_201_CREATED,
)
def create_employee_compensation_revision(
    payload: CompensationHistoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permissions("PAYROLL.COMPENSATION_MANAGE")
    ),
):
    return create_compensation_revision(
        db=db,
        payload=payload,
        actor_user_id=current_user.id,
    )
