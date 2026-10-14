
from sqlalchemy.orm import Session, joinedload, selectinload
from fastapi import HTTPException, status

from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.schemas.user import UserUpdate


def _user_query(db: Session):
    return db.query(User).options(
        selectinload(User.user_roles).joinedload(UserRole.role),
        selectinload(User.employee),
    )


def list_users(db: Session) -> list[User]:
    return (
        _user_query(db)
        .order_by(User.id.asc())
        .all()
    )


def get_user_or_404(db: Session, user_id: int) -> User:
    user = _user_query(db).filter(User.id == user_id).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    return user


def serialize_user(user: User) -> dict:
    active_roles = sorted(
        {
            assignment.role.name
            for assignment in user.user_roles
            if assignment.role is not None
            and assignment.role.is_active
        }
    )

    employee = user.employee

    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_active": user.is_active,
        "roles": active_roles,
        "employee_id": employee.id if employee else None,
        "employee_code": (
            employee.employee_code if employee else None
        ),
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }


def count_active_admin_users(db: Session) -> int:
    return (
        db.query(User.id)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .filter(
            User.is_active.is_(True),
            Role.is_active.is_(True),
            Role.name == "ADMIN",
        )
        .distinct()
        .count()
    )


def update_user(
    db: Session,
    user: User,
    payload: UserUpdate,
) -> User:
    changes = payload.model_dump(exclude_unset=True)

    if changes.get("first_name") is not None:
        user.first_name = changes["first_name"]

    if changes.get("last_name") is not None:
        user.last_name = changes["last_name"]

    if changes.get("is_active") is not None:
        user.is_active = changes["is_active"]

    try:
        db.add(user)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return get_user_or_404(db, user.id)
