
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.department import Department
from app.models.designation import Designation
from app.schemas.designation import DesignationCreate, DesignationUpdate


def get_department_or_error(
    db: Session,
    department_id: int,
) -> Department:
    department = db.get(Department, department_id)

    if department is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found",
        )

    if not department.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot use an inactive department",
        )

    return department


def list_designations(db: Session) -> list[Designation]:
    statement = select(Designation).order_by(
        Designation.department_id,
        Designation.name,
    )
    return list(db.scalars(statement).all())


def get_designation(
    db: Session,
    designation_id: int,
) -> Designation:
    designation = db.get(Designation, designation_id)

    if designation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Designation not found",
        )

    return designation


def create_designation(
    db: Session,
    payload: DesignationCreate,
) -> Designation:
    name = payload.name.strip()

    if not name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Designation name cannot be empty",
        )

    get_department_or_error(db, payload.department_id)

    designation = Designation(
        name=name,
        department_id=payload.department_id,
        level=payload.level,
        is_active=True,
    )

    db.add(designation)

    try:
        db.commit()
        db.refresh(designation)
        return designation
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This designation already exists in the department",
        ) from None


def update_designation(
    db: Session,
    designation_id: int,
    payload: DesignationUpdate,
) -> Designation:
    designation = get_designation(db, designation_id)
    changes = payload.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least one field to update",
        )

    if "name" in changes:
        name = changes["name"]

        if name is None or not name.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Designation name cannot be empty",
            )

        changes["name"] = name.strip()

    if "department_id" in changes:
        department_id = changes["department_id"]

        if department_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Department ID cannot be null",
            )

        get_department_or_error(db, department_id)

    for field, value in changes.items():
        setattr(designation, field, value)

    try:
        db.commit()
        db.refresh(designation)
        return designation
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This designation already exists in the department",
        ) from None


def deactivate_designation(
    db: Session,
    designation_id: int,
) -> Designation:
    designation = get_designation(db, designation_id)
    designation.is_active = False

    db.commit()
    db.refresh(designation)

    return designation
