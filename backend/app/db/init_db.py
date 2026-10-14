
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import Role, User, UserRole
from decimal import Decimal

from app.models.leave_type import LeaveType

ROLE_DEFINITIONS = {
    "ADMIN": "Full administrative access",
    "HR": "Human resources operations",
    "EMPLOYEE": "Employee self-service access",
}


def get_or_create_role(
    db: Session,
    name: str,
    description: str,
) -> Role:
    role = db.scalar(
        select(Role).where(Role.name == name)
    )

    if role is None:
        role = Role(
            name=name,
            description=description,
            is_active=True,
        )
        db.add(role)
        db.flush()

    return role


def ensure_demo_user(
    db: Session,
    email: str,
    password: str,
    first_name: str,
    last_name: str,
    role: Role,
) -> User:
    email = email.strip().lower()

    user = db.scalar(
        select(User).where(User.email == email)
    )

    if user is None:
        user = User(
            email=email,
            password_hash=hash_password(password),
            first_name=first_name,
            last_name=last_name,
            is_active=True,
        )
        db.add(user)
        db.flush()

    existing_assignment = db.scalar(
        select(UserRole).where(
            UserRole.user_id == user.id,
            UserRole.role_id == role.id,
        )
    )

    if existing_assignment is None:
        db.add(
            UserRole(
                user_id=user.id,
                role_id=role.id,
            )
        )

    return user


def main() -> None:
    if settings.app_env.lower() != "development":
        raise RuntimeError(
            "Demo seeding is allowed only in development."
        )

    demo_accounts = [
        (
            settings.demo_admin_email,
            settings.demo_admin_password,
            "Demo",
            "Admin",
            "ADMIN",
        ),
        (
            settings.demo_hr_email,
            settings.demo_hr_password,
            "Demo",
            "HR",
            "HR",
        ),
        (
            settings.demo_employee_email,
            settings.demo_employee_password,
            "Demo",
            "Employee",
            "EMPLOYEE",
        ),
    ]

    if any(password is None for _, password, *_ in demo_accounts):
        raise RuntimeError(
            "Set all three DEMO_*_PASSWORD values in backend/.env."
        )

    with SessionLocal() as db:
        try:
            roles = {
                name: get_or_create_role(db, name, description)
                for name, description in ROLE_DEFINITIONS.items()
            }

            for email, password, first_name, last_name, role_name in demo_accounts:
                assert password is not None

                ensure_demo_user(
                    db=db,
                    email=email,
                    password=password.get_secret_value(),
                    first_name=first_name,
                    last_name=last_name,
                    role=roles[role_name],
                )
            default_leave_types = [
                {
                    "code": "CASUAL",
                    "name": "Casual Leave",
                    "description": "Casual leave for personal needs",
                    "is_paid": True,
                    "annual_quota": Decimal("12.00"),
                },
                {
                    "code": "SICK",
                    "name": "Sick Leave",
                    "description": "Leave for illness or medical needs",
                    "is_paid": True,
                    "annual_quota": Decimal("12.00"),
                },
                {
                    "code": "EARNED",
                    "name": "Earned Leave",
                    "description": "Annual earned leave",
                    "is_paid": True,
                    "annual_quota": Decimal("15.00"),
                },
                {
                    "code": "LOP",
                    "name": "Loss of Pay",
                    "description": "Unpaid leave",
                    "is_paid": False,
                    "annual_quota": Decimal("0.00"),
                },
            ]

            for item in default_leave_types:
                existing = db.scalar(
                    select(LeaveType).where(LeaveType.code == item["code"])
                )

                if existing is None:
                    db.add(LeaveType(**item))
            db.commit()

        except Exception:
            db.rollback()
            raise

    print("Demo roles and users are ready.")
    for email, _, _, _, role_name in demo_accounts:
        print(f"{role_name}: {email}")


if __name__ == "__main__":
    main()
