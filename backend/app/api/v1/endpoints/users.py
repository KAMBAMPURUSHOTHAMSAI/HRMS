
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.permissions import require_permissions
from app.models.user import User
from app.schemas.user import UserRead, UserUpdate
from app.services.user_service import (
    count_active_admin_users,
    get_user_or_404,
    list_users,
    serialize_user,
    update_user,
)


router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


def _has_role(user: User, role_name: str) -> bool:
    return any(
        assignment.role is not None
        and assignment.role.is_active
        and assignment.role.name == role_name
        for assignment in user.user_roles
    )


@router.get(
    "",
    response_model=list[UserRead],
    dependencies=[
        Depends(require_permissions("USERS.READ"))
    ],
)
def read_users(db: Session = Depends(get_db)):
    return [
        serialize_user(user)
        for user in list_users(db)
    ]


@router.get(
    "/{user_id}",
    response_model=UserRead,
    dependencies=[
        Depends(require_permissions("USERS.READ"))
    ],
)
def read_user(
    user_id: int,
    db: Session = Depends(get_db),
):
    user = get_user_or_404(db, user_id)
    return serialize_user(user)


@router.patch(
    "/{user_id}",
    response_model=UserRead,
)
def edit_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permissions("USERS.UPDATE")
    ),
):
    target_user = get_user_or_404(db, user_id)

    changes = payload.model_dump(exclude_unset=True)
    requested_active_status = changes.get("is_active")

    status_is_changing = (
        requested_active_status is not None
        and requested_active_status != target_user.is_active
    )

    if status_is_changing:
        if not _has_role(current_user, "ADMIN"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only an Admin can change a user's account status.",
            )

        if (
            requested_active_status is False
            and current_user.id == target_user.id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot deactivate your own account.",
            )

        if (
            requested_active_status is False
            and target_user.is_active
            and _has_role(target_user, "ADMIN")
            and count_active_admin_users(db) <= 1
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The last active Admin account cannot be deactivated.",
            )

    updated_user = update_user(
        db,
        target_user,
        payload,
    )

    return serialize_user(updated_user)
