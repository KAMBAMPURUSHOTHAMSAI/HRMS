
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user import User
from app.models.user_role import UserRole
from app.schemas.role import (
    PermissionCreate,
    PermissionUpdate,
    RoleCreate,
    RoleUpdate,
)


def _role_query(db: Session):
    return db.query(Role).options(
        selectinload(Role.user_roles),
        selectinload(Role.role_permissions).joinedload(
            RolePermission.permission
        ),
    )


def list_roles(db: Session) -> list[Role]:
    return _role_query(db).order_by(Role.name.asc()).all()


def get_role_or_404(db: Session, role_id: int) -> Role:
    role = _role_query(db).filter(Role.id == role_id).first()

    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found.",
        )

    return role


def serialize_role(role: Role) -> dict:
    return {
        "id": role.id,
        "name": role.name,
        "description": role.description,
        "is_active": role.is_active,
        "permission_ids": sorted(
            {
                assignment.permission_id
                for assignment in role.role_permissions
            }
        ),
        "user_ids": sorted(
            {
                assignment.user_id
                for assignment in role.user_roles
            }
        ),
        "user_count": len(
            {assignment.user_id for assignment in role.user_roles}
        ),
    }


def list_permissions(db: Session) -> list[Permission]:
    return db.query(Permission).order_by(Permission.code.asc()).all()


def get_permission_or_404(
    db: Session,
    permission_id: int,
) -> Permission:
    permission = db.get(Permission, permission_id)

    if permission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found.",
        )

    return permission


def serialize_permission(permission: Permission) -> dict:
    return {
        "id": permission.id,
        "code": permission.code,
        "description": permission.description,
    }


def create_role(db: Session, payload: RoleCreate) -> Role:
    existing = db.query(Role).filter(
        func.upper(Role.name) == payload.name
    ).first()

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A role with this name already exists.",
        )

    role = Role(
        name=payload.name,
        description=payload.description,
        is_active=True,
    )

    try:
        db.add(role)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A role with this name already exists.",
        ) from None
    except Exception:
        db.rollback()
        raise

    return get_role_or_404(db, role.id)


def update_role(
    db: Session,
    role_id: int,
    payload: RoleUpdate,
) -> Role:
    role = get_role_or_404(db, role_id)
    changes = payload.model_dump(exclude_unset=True)

    name = changes.get("name")

    if name is not None:
        duplicate = db.query(Role).filter(
            func.upper(Role.name) == name,
            Role.id != role.id,
        ).first()

        if duplicate is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A role with this name already exists.",
            )

    requested_active_status = changes.get("is_active")

    if requested_active_status is False and role.is_active:
        if role.name == "ADMIN":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The built-in ADMIN role cannot be deactivated.",
            )

        if role.user_roles:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Remove this role from its assigned users before "
                    "deactivating it."
                ),
            )

    if name is not None:
        role.name = name

    if "description" in changes:
        role.description = changes["description"]

    if requested_active_status is not None:
        role.is_active = requested_active_status

    try:
        db.add(role)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The role update conflicts with existing data.",
        ) from None
    except Exception:
        db.rollback()
        raise

    return get_role_or_404(db, role.id)


def create_permission(
    db: Session,
    payload: PermissionCreate,
) -> Permission:
    existing = db.query(Permission).filter(
        func.upper(Permission.code) == payload.code
    ).first()

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A permission with this code already exists.",
        )

    permission = Permission(
        code=payload.code,
        description=payload.description,
    )

    try:
        db.add(permission)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A permission with this code already exists.",
        ) from None
    except Exception:
        db.rollback()
        raise

    return get_permission_or_404(db, permission.id)


def update_permission(
    db: Session,
    permission_id: int,
    payload: PermissionUpdate,
) -> Permission:
    permission = get_permission_or_404(db, permission_id)
    changes = payload.model_dump(exclude_unset=True)

    code = changes.get("code")

    if code is not None:
        duplicate = db.query(Permission).filter(
            func.upper(Permission.code) == code,
            Permission.id != permission.id,
        ).first()

        if duplicate is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A permission with this code already exists.",
            )

        permission.code = code

    if "description" in changes:
        permission.description = changes["description"]

    try:
        db.add(permission)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The permission update conflicts with existing data.",
        ) from None
    except Exception:
        db.rollback()
        raise

    return get_permission_or_404(db, permission.id)


def delete_permission(db: Session, permission_id: int) -> None:
    permission = get_permission_or_404(db, permission_id)

    assignment = db.query(RolePermission).filter(
        RolePermission.permission_id == permission_id
    ).first()

    if assignment is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Remove this permission from all roles before deleting it."
            ),
        )

    try:
        db.delete(permission)
        db.commit()
    except Exception:
        db.rollback()
        raise


def assign_user_to_role(
    db: Session,
    role_id: int,
    user_id: int,
) -> Role:
    role = get_role_or_404(db, role_id)
    user = db.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if not role.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot assign an inactive role.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot assign a role to an inactive user.",
        )

    existing = db.get(UserRole, (user_id, role_id))

    if existing is not None:
        return get_role_or_404(db, role_id)

    try:
        db.add(UserRole(user_id=user_id, role_id=role_id))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The role assignment already exists or conflicts.",
        ) from None
    except Exception:
        db.rollback()
        raise

    return get_role_or_404(db, role_id)


def remove_user_from_role(
    db: Session,
    role_id: int,
    user_id: int,
) -> Role:
    role = get_role_or_404(db, role_id)
    user = db.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    assignment = db.get(UserRole, (user_id, role_id))

    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This user is not assigned to the selected role.",
        )

    if role.name == "ADMIN" and user.is_active:
        active_admin_count = (
            db.query(User.id)
            .join(UserRole, UserRole.user_id == User.id)
            .filter(
                UserRole.role_id == role.id,
                User.is_active.is_(True),
            )
            .count()
        )

        if active_admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The last active Admin cannot lose the ADMIN role.",
            )

    try:
        db.delete(assignment)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return get_role_or_404(db, role_id)


def assign_permission_to_role(
    db: Session,
    role_id: int,
    permission_id: int,
) -> Role:
    role = get_role_or_404(db, role_id)

    if not role.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot assign permissions to an inactive role.",
        )

    get_permission_or_404(db, permission_id)

    existing = db.get(RolePermission, (role_id, permission_id))

    if existing is not None:
        return get_role_or_404(db, role_id)

    try:
        db.add(
            RolePermission(
                role_id=role_id,
                permission_id=permission_id,
            )
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The permission assignment already exists or conflicts.",
        ) from None
    except Exception:
        db.rollback()
        raise

    return get_role_or_404(db, role_id)


def remove_permission_from_role(
    db: Session,
    role_id: int,
    permission_id: int,
) -> Role:
    get_role_or_404(db, role_id)

    assignment = db.get(RolePermission, (role_id, permission_id))

    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This permission is not assigned to the selected role.",
        )

    try:
        db.delete(assignment)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return get_role_or_404(db, role_id)
