
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.salary_component import SalaryComponent
from app.schemas.salary_component import (
    SalaryComponentCreate,
    SalaryComponentUpdate,
)


def list_salary_components(
    db: Session,
    include_inactive: bool = True,
) -> list[SalaryComponent]:
    query = select(SalaryComponent)

    if not include_inactive:
        query = query.where(SalaryComponent.is_active.is_(True))

    query = query.order_by(SalaryComponent.name.asc())

    return list(db.scalars(query).all())


def _get_component_or_404(
    db: Session,
    component_id: int,
) -> SalaryComponent:
    component = db.get(SalaryComponent, component_id)

    if component is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salary component not found",
        )

    return component


def create_salary_component(
    db: Session,
    payload: SalaryComponentCreate,
    actor_user_id: int,
) -> SalaryComponent:
    values = payload.model_dump()
    values["code"] = payload.code.strip().upper()
    values["name"] = payload.name.strip()

    existing = db.scalar(
        select(SalaryComponent.id).where(
            SalaryComponent.code == values["code"]
        )
    )

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A salary component with this code already exists",
        )

    component = SalaryComponent(
        **values,
        created_by_user_id=actor_user_id,

    )

    db.add(component)

    try:
        db.commit()
        db.refresh(component)
        return component
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not create salary component. Check for duplicate values.",
        ) from exc
    except Exception:
        db.rollback()
        raise


def update_salary_component(
    db: Session,
    component_id: int,
    payload: SalaryComponentUpdate,
) -> SalaryComponent:
    component = _get_component_or_404(db, component_id)
    changes = payload.model_dump(exclude_unset=True)

    if "code" in changes and changes["code"] is not None:
        changes["code"] = changes["code"].strip().upper()

        duplicate = db.scalar(
            select(SalaryComponent.id).where(
                SalaryComponent.code == changes["code"],
                SalaryComponent.id != component_id,
            )
        )

        if duplicate is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A salary component with this code already exists",
            )

    if "name" in changes and changes["name"] is not None:
        changes["name"] = changes["name"].strip()

    for field, value in changes.items():
        setattr(component, field, value)

    try:
        db.commit()
        db.refresh(component)
        return component
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not update salary component because of a data conflict",
        ) from exc
    except Exception:
        db.rollback()
        raise


def deactivate_salary_component(
    db: Session,
    component_id: int,
) -> SalaryComponent:
    component = _get_component_or_404(db, component_id)

    component.is_active = False

    try:
        db.commit()
        db.refresh(component)
        return component
    except Exception:
        db.rollback()
        raise
