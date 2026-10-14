
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.department import Department
from app.schemas.department import DepartmentCreate, DepartmentUpdate


def list_departments(db: Session) -> list[Department]:
    statement = select(Department).order_by(Department.name)
    return list(db.scalars(statement).all())


def get_department(db: Session, department_id: int) -> Department:
    department = db.get(Department, department_id)

    if department is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found",
        )

    return department


def create_department(
    db: Session,
    payload: DepartmentCreate,
) -> Department:
    name = payload.name.strip()

    if not name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Department name cannot be empty",
        )

    department = Department(
        name=name,
        description=payload.description,
        is_active=True,
    )

    db.add(department)

    try:
        db.commit()
        db.refresh(department)
        return department
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A department with this name already exists",
        ) from None


def update_department(
    db: Session,
    department_id: int,
    payload: DepartmentUpdate,
) -> Department:
    department = get_department(db, department_id)
    changes = payload.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least one field to update",
        )

    if "name" in changes:
        if changes["name"] is None or not changes["name"].strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Department name cannot be empty",
            )

        changes["name"] = changes["name"].strip()

    for field, value in changes.items():
        setattr(department, field, value)

    try:
        db.commit()
        db.refresh(department)
        return department
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A department with this name already exists",
        ) from None


def deactivate_department(
    db: Session,
    department_id: int,
) -> Department:
    department = get_department(db, department_id)
    department.is_active = False

    db.commit()
    db.refresh(department)

    return department
