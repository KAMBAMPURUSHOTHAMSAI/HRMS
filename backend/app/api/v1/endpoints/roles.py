
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.permissions import require_permissions
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user import User
from app.models.user_role import UserRole
from app.schemas.role import (
    PermissionCreate,
    PermissionRead,
    PermissionUpdate,
    RoleCreate,
    RoleRead,
    RoleUpdate,
)
from app.services.audit_service import record_audit_event
from app.services.role_service import (
    assign_permission_to_role,
    assign_user_to_role,
    create_permission,
    create_role,
    delete_permission,
    get_permission_or_404,
    get_role_or_404,
    list_permissions,
    list_roles,
    remove_permission_from_role,
    remove_user_from_role,
    serialize_permission,
    serialize_role,
    update_permission,
    update_role,
)


router = APIRouter(
    prefix="/roles",
    tags=["Roles & Permissions"],
)

BUILT_IN_ROLES = {"ADMIN", "HR", "EMPLOYEE"}


def _record_change(
    db: Session,
    request: Request,
    actor: User,
    *,
    action: str,
    entity_type: str,
    description: str,
    entity_id: int | str | None = None,
    details: dict | None = None,
):
    """Add an audit entry to the current SQLAlchemy transaction."""
    return record_audit_event(
        db,
        action=action,
        entity_type=entity_type,
        description=description,
        actor=actor,
        entity_id=entity_id,
        details=details or {},
        request=request,
    )


def _commit_pending_audit(db: Session) -> None:
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


# ---------------------------------------------------------
# PERMISSIONS
# ---------------------------------------------------------

@router.get(
    "/permissions",
    response_model=list[PermissionRead],
    dependencies=[
        Depends(require_permissions("PERMISSIONS.READ"))
    ],
)
def read_permissions(db: Session = Depends(get_db)):
    return [
        serialize_permission(item)
        for item in list_permissions(db)
    ]


@router.post(
    "/permissions",
    response_model=PermissionRead,
    status_code=status.HTTP_201_CREATED,
)
def add_permission(
    payload: PermissionCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(
        require_permissions("PERMISSIONS.MANAGE")
    ),
):
    event = _record_change(
        db,
        request,
        actor,
        action="CREATE",
        entity_type="PERMISSION",
        description=f"Created permission {payload.code}",
        details={"code": payload.code},
    )

    permission = create_permission(db, payload)

    event.entity_id = str(permission.id)
    _commit_pending_audit(db)

    return serialize_permission(permission)


@router.patch(
    "/permissions/{permission_id}",
    response_model=PermissionRead,
)
def edit_permission(
    permission_id: int,
    payload: PermissionUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(
        require_permissions("PERMISSIONS.MANAGE")
    ),
):
    permission = get_permission_or_404(db, permission_id)

    # Permission codes are referenced by application authorization.
    # Renaming a code could silently remove access from existing roles.
    if payload.code is not None and payload.code != permission.code:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Permission codes cannot be renamed. "
                "Update the description instead."
            ),
        )

    event = _record_change(
        db,
        request,
        actor,
        action="UPDATE",
        entity_type="PERMISSION",
        entity_id=permission.id,
        description=f"Updated permission {permission.code}",
        details={
            "permission_code": permission.code,
            "description_changed": (
                "description" in payload.model_fields_set
            ),
        },
    )

    updated = update_permission(
        db,
        permission_id,
        payload,
    )

    event.entity_id = str(updated.id)
    _commit_pending_audit(db)

    return serialize_permission(updated)


@router.delete(
    "/permissions/{permission_id}",
)
def remove_permission(
    permission_id: int,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(
        require_permissions("PERMISSIONS.MANAGE")
    ),
):
    permission = get_permission_or_404(db, permission_id)

    _record_change(
        db,
        request,
        actor,
        action="DELETE",
        entity_type="PERMISSION",
        entity_id=permission.id,
        description=f"Deleted permission {permission.code}",
        details={"code": permission.code},
    )

    delete_permission(db, permission_id)
    _commit_pending_audit(db)

    return {"message": "Permission deleted successfully."}


# ---------------------------------------------------------
# ROLES
# ---------------------------------------------------------

@router.get(
    "",
    response_model=list[RoleRead],
    dependencies=[
        Depends(require_permissions("ROLES.READ"))
    ],
)
def read_roles(db: Session = Depends(get_db)):
    return [
        serialize_role(role)
        for role in list_roles(db)
    ]


@router.get(
    "/{role_id}",
    response_model=RoleRead,
    dependencies=[
        Depends(require_permissions("ROLES.READ"))
    ],
)
def read_role(
    role_id: int,
    db: Session = Depends(get_db),
):
    return serialize_role(
        get_role_or_404(db, role_id)
    )


@router.post(
    "",
    response_model=RoleRead,
    status_code=status.HTTP_201_CREATED,
)
def add_role(
    payload: RoleCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(
        require_permissions("ROLES.MANAGE")
    ),
):
    event = _record_change(
        db,
        request,
        actor,
        action="CREATE",
        entity_type="ROLE",
        description=f"Created role {payload.name}",
        details={"name": payload.name},
    )

    role = create_role(db, payload)

    event.entity_id = str(role.id)
    _commit_pending_audit(db)

    return serialize_role(role)


@router.patch(
    "/{role_id}",
    response_model=RoleRead,
)
def edit_role(
    role_id: int,
    payload: RoleUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(
        require_permissions("ROLES.MANAGE")
    ),
):
    role = get_role_or_404(db, role_id)
    changes = payload.model_dump(exclude_unset=True)

    if role.name in BUILT_IN_ROLES:
        requested_name = changes.get("name")

        if requested_name is not None and requested_name != role.name:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Built-in role names cannot be changed.",
            )

        if changes.get("is_active") is False:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Built-in roles cannot be deactivated.",
            )

    event = _record_change(
        db,
        request,
        actor,
        action="UPDATE",
        entity_type="ROLE",
        entity_id=role.id,
        description=f"Updated role {role.name}",
        details={"changed_fields": sorted(changes.keys())},
    )

    updated = update_role(db, role_id, payload)

    event.entity_id = str(updated.id)
    _commit_pending_audit(db)

    return serialize_role(updated)


@router.delete(
    "/{role_id}",
    response_model=RoleRead,
)
def deactivate_role(
    role_id: int,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(
        require_permissions("ROLES.MANAGE")
    ),
):
    role = get_role_or_404(db, role_id)

    if role.name in BUILT_IN_ROLES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Built-in roles cannot be deactivated.",
        )

    event = _record_change(
        db,
        request,
        actor,
        action="DEACTIVATE",
        entity_type="ROLE",
        entity_id=role.id,
        description=f"Deactivated role {role.name}",
        details={"name": role.name},
    )

    updated = update_role(
        db,
        role_id,
        RoleUpdate(is_active=False),
    )

    event.entity_id = str(updated.id)
    _commit_pending_audit(db)

    return serialize_role(updated)


# ---------------------------------------------------------
# USER ↔ ROLE ASSIGNMENTS
# ---------------------------------------------------------

@router.post(
    "/{role_id}/users/{user_id}",
    response_model=RoleRead,
)
def add_user_to_role(
    role_id: int,
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(
        require_permissions("ROLES.MANAGE")
    ),
):
    role = get_role_or_404(db, role_id)
    existing = db.get(UserRole, (user_id, role_id))

    if existing is not None:
        return serialize_role(role)

    event = _record_change(
        db,
        request,
        actor,
        action="ASSIGN",
        entity_type="USER_ROLE",
        entity_id=user_id,
        description=f"Assigned user {user_id} to role {role.name}",
        details={
            "user_id": user_id,
            "role_id": role_id,
            "role_name": role.name,
        },
    )

    updated = assign_user_to_role(
        db,
        role_id,
        user_id,
    )

    event.entity_id = str(user_id)
    _commit_pending_audit(db)

    return serialize_role(updated)


@router.delete(
    "/{role_id}/users/{user_id}",
    response_model=RoleRead,
)
def remove_user_role(
    role_id: int,
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(
        require_permissions("ROLES.MANAGE")
    ),
):
    role = get_role_or_404(db, role_id)

    if role.name == "ADMIN" and actor.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot remove your own ADMIN role.",
        )

    if db.get(UserRole, (user_id, role_id)) is None:
        # Let the service provide the established 404 response.
        remove_user_from_role(db, role_id, user_id)

    event = _record_change(
        db,
        request,
        actor,
        action="REMOVE",
        entity_type="USER_ROLE",
        entity_id=user_id,
        description=f"Removed user {user_id} from role {role.name}",
        details={
            "user_id": user_id,
            "role_id": role_id,
            "role_name": role.name,
        },
    )

    updated = remove_user_from_role(
        db,
        role_id,
        user_id,
    )

    _commit_pending_audit(db)

    return serialize_role(updated)


# ---------------------------------------------------------
# ROLE ↔ PERMISSION ASSIGNMENTS
# ---------------------------------------------------------

@router.post(
    "/{role_id}/permissions/{permission_id}",
    response_model=RoleRead,
)
def add_permission_to_role(
    role_id: int,
    permission_id: int,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(
        require_permissions("PERMISSIONS.MANAGE")
    ),
):
    role = get_role_or_404(db, role_id)
    permission = get_permission_or_404(db, permission_id)

    if db.get(RolePermission, (role_id, permission_id)) is not None:
        return serialize_role(role)

    event = _record_change(
        db,
        request,
        actor,
        action="ASSIGN",
        entity_type="ROLE_PERMISSION",
        entity_id=role_id,
        description=(
            f"Assigned permission {permission.code} to role {role.name}"
        ),
        details={
            "role_id": role_id,
            "role_name": role.name,
            "permission_id": permission_id,
            "permission_code": permission.code,
        },
    )

    updated = assign_permission_to_role(
        db,
        role_id,
        permission_id,
    )

    event.entity_id = str(role_id)
    _commit_pending_audit(db)

    return serialize_role(updated)


@router.delete(
    "/{role_id}/permissions/{permission_id}",
    response_model=RoleRead,
)
def remove_role_permission(
    role_id: int,
    permission_id: int,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(
        require_permissions("PERMISSIONS.MANAGE")
    ),
):
    role = get_role_or_404(db, role_id)
    permission = get_permission_or_404(db, permission_id)

    if role.name == "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Permissions cannot be removed from the ADMIN role.",
        )

    event = _record_change(
        db,
        request,
        actor,
        action="REMOVE",
        entity_type="ROLE_PERMISSION",
        entity_id=role_id,
        description=(
            f"Removed permission {permission.code} from role {role.name}"
        ),
        details={
            "role_id": role_id,
            "role_name": role.name,
            "permission_id": permission_id,
            "permission_code": permission.code,
        },
    )

    updated = remove_permission_from_role(
        db,
        role_id,
        permission_id,
    )

    _commit_pending_audit(db)

    return serialize_role(updated)
