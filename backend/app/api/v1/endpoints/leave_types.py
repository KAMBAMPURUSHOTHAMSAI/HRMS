
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.permissions import require_permissions
from app.models.user import User
from app.schemas.leave import (
    LeaveTypeCreate,
    LeaveTypeRead,
    LeaveTypeUpdate,
)
from app.services.leave_type_service import (
    create_leave_type,
    deactivate_leave_type,
    list_leave_types,
    update_leave_type,
)


router = APIRouter(
    prefix="/leave-types",
    tags=["Leave Types"],
)


@router.get("", response_model=list[LeaveTypeRead])
def read_leave_types(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permissions("LEAVE_TYPES.READ")
    ),
):
    active_roles = {
        item.role.name
        for item in current_user.user_roles
        if item.role and item.role.is_active
    }

    if include_inactive and not active_roles.intersection(
        {"ADMIN", "HR"}
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot view inactive leave types.",
        )

    return list_leave_types(db, include_inactive)


@router.post(
    "",
    response_model=LeaveTypeRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(require_permissions("LEAVE_TYPES.CREATE"))
    ],
)
def add_leave_type(
    payload: LeaveTypeCreate,
    db: Session = Depends(get_db),
):
    return create_leave_type(db, payload)


@router.patch(
    "/{leave_type_id}",
    response_model=LeaveTypeRead,
    dependencies=[
        Depends(require_permissions("LEAVE_TYPES.UPDATE"))
    ],
)
def edit_leave_type(
    leave_type_id: int,
    payload: LeaveTypeUpdate,
    db: Session = Depends(get_db),
):
    return update_leave_type(db, leave_type_id, payload)


@router.delete(
    "/{leave_type_id}",
    response_model=LeaveTypeRead,
    dependencies=[
        Depends(require_permissions("LEAVE_TYPES.DELETE"))
    ],
)
def remove_leave_type(
    leave_type_id: int,
    db: Session = Depends(get_db),
):
    return deactivate_leave_type(db, leave_type_id)
