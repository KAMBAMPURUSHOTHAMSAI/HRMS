
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.permissions import require_permissions
from app.models.user import User
from app.schemas.payroll_component_line import PayrollComponentLineRead
from app.services.payroll_component_line_service import (
    create_payroll_component_snapshot,
    list_payroll_component_lines,
)


router = APIRouter(
    prefix="/payroll-component-lines",
    tags=["Payroll Component Breakdown"],
)


@router.get(
    "/{payroll_record_id}",
    response_model=list[PayrollComponentLineRead],
)
def read_payroll_component_lines(
    payroll_record_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(
        require_permissions("PAYROLL.COMPONENTS_READ")
    ),
):
    return list_payroll_component_lines(
        db=db,
        payroll_record_id=payroll_record_id,
    )


@router.post(
    "/{payroll_record_id}/snapshot",
    response_model=list[PayrollComponentLineRead],
    status_code=status.HTTP_201_CREATED,
)
def create_payroll_snapshot(
    payroll_record_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(
        require_permissions("PAYROLL.COMPONENTS_MANAGE")
    ),
):
    return create_payroll_component_snapshot(
        db=db,
        payroll_record_id=payroll_record_id,
    )
