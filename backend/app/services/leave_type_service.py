from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.leave_type import LeaveType
from app.schemas.leave import LeaveTypeCreate, LeaveTypeUpdate


def list_leave_types(
    db: Session,
    include_inactive: bool = False,
) -> list[LeaveType]:
    statement = select(LeaveType).order_by(LeaveType.name)

    if not include_inactive:
        statement = statement.where(LeaveType.is_active.is_(True))

    return list(db.scalars(statement).all())


def create_leave_type(
    db: Session,
    payload: LeaveTypeCreate,
) -> LeaveType:
    if payload.is_paid and payload.annual_quota <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Paid leave types must have a positive annual quota",
        )

    leave_type = LeaveType(
        code=payload.code,
        name=payload.name,
        description=payload.description,
        is_paid=payload.is_paid,
        annual_quota=payload.annual_quota,
        is_active=True,
    )

    db.add(leave_type)

    try:
        db.commit()
        db.refresh(leave_type)
        return leave_type
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Leave type code or name already exists",
        ) from None


def update_leave_type(
    db: Session,
    leave_type_id: int,
    payload: LeaveTypeUpdate,
) -> LeaveType:
    leave_type = db.get(LeaveType, leave_type_id)

    if leave_type is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Leave type not found",
        )

    changes = payload.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least one field to update",
        )

    paid = changes.get("is_paid", leave_type.is_paid)
    quota = changes.get("annual_quota", leave_type.annual_quota)

    if paid and (quota is None or quota <= 0):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Paid leave types must have a positive annual quota",
        )

    if "name" in changes:
        if changes["name"] is None or not changes["name"].strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Leave type name cannot be empty",
            )
        changes["name"] = changes["name"].strip()

    for field, value in changes.items():
        setattr(leave_type, field, value)

    try:
        db.commit()
        db.refresh(leave_type)
        return leave_type
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Leave type name already exists",
        ) from None


def deactivate_leave_type(
    db: Session,
    leave_type_id: int,
) -> LeaveType:
    leave_type = db.get(LeaveType, leave_type_id)

    if leave_type is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Leave type not found",
        )

    leave_type.is_active = False
    db.commit()
    db.refresh(leave_type)

    return leave_type