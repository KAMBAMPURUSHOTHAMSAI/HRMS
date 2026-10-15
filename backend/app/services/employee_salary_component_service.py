
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.employee_salary_component import EmployeeSalaryComponent
from app.models.salary_component import SalaryComponent
from app.schemas.employee_salary_component import (
    EmployeeSalaryComponentCreate,
    EmployeeSalaryComponentUpdate,
)


def _get_assignment_or_404(
    db: Session,
    assignment_id: int,
) -> EmployeeSalaryComponent:
    assignment = db.get(EmployeeSalaryComponent, assignment_id)

    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee salary component assignment not found",
        )

    return assignment


def _validate_dates(
    effective_from: date,
    effective_to: date | None,
) -> None:
    if effective_to is not None and effective_to < effective_from:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="effective_to cannot be earlier than effective_from",
        )


def _validate_no_overlap(
    db: Session,
    employee_id: int,
    component_id: int,
    effective_from: date,
    effective_to: date | None,
    exclude_assignment_id: int | None = None,
) -> None:
    query = select(EmployeeSalaryComponent).where(
        EmployeeSalaryComponent.employee_id == employee_id,
        EmployeeSalaryComponent.component_id == component_id,
    )

    if exclude_assignment_id is not None:
        query = query.where(
            EmployeeSalaryComponent.id != exclude_assignment_id
        )

    existing_assignments = db.scalars(query).all()
    new_end = effective_to or date.max

    for existing in existing_assignments:
        existing_end = existing.effective_to or date.max

        overlaps = (
            effective_from <= existing_end
            and existing.effective_from <= new_end
        )

        if overlaps:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "This employee already has an overlapping "
                    "effective period for this salary component"
                ),
            )


def list_employee_salary_components(
    db: Session,
    employee_id: int | None = None,
    as_of_date: date | None = None,
) -> list[EmployeeSalaryComponent]:
    query = select(EmployeeSalaryComponent)

    if employee_id is not None:
        employee = db.get(Employee, employee_id)

        if employee is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee not found",
            )

        query = query.where(
            EmployeeSalaryComponent.employee_id == employee_id
        )

    if as_of_date is not None:
        query = query.where(
            EmployeeSalaryComponent.effective_from <= as_of_date
        ).where(
            (EmployeeSalaryComponent.effective_to.is_(None))
            | (EmployeeSalaryComponent.effective_to >= as_of_date)
        )

    query = query.order_by(
        EmployeeSalaryComponent.employee_id,
        EmployeeSalaryComponent.component_id,
        EmployeeSalaryComponent.effective_from.desc(),
    )

    return list(db.scalars(query).all())


def create_employee_salary_component(
    db: Session,
    payload: EmployeeSalaryComponentCreate,
    actor_user_id: int,
) -> EmployeeSalaryComponent:
    employee = db.get(Employee, payload.employee_id)

    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )

    component = db.get(SalaryComponent, payload.component_id)

    if component is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salary component not found",
        )

    if not component.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot assign an inactive salary component",
        )

    _validate_dates(payload.effective_from, payload.effective_to)

    _validate_no_overlap(
        db=db,
        employee_id=payload.employee_id,
        component_id=payload.component_id,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
    )

    assignment = EmployeeSalaryComponent(
        **payload.model_dump(),
        assigned_by_user_id=actor_user_id,
    )

    db.add(assignment)

    try:
        db.commit()
        db.refresh(assignment)
        return assignment
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not assign the salary component due to a data conflict",
        ) from exc
    except Exception:
        db.rollback()
        raise


def update_employee_salary_component(
    db: Session,
    assignment_id: int,
    payload: EmployeeSalaryComponentUpdate,
) -> EmployeeSalaryComponent:
    assignment = _get_assignment_or_404(db, assignment_id)
    changes = payload.model_dump(exclude_unset=True)

    effective_from = changes.get(
        "effective_from",
        assignment.effective_from,
    )
    effective_to = changes.get(
        "effective_to",
        assignment.effective_to,
    )

    _validate_dates(effective_from, effective_to)

    _validate_no_overlap(
        db=db,
        employee_id=assignment.employee_id,
        component_id=assignment.component_id,
        effective_from=effective_from,
        effective_to=effective_to,
        exclude_assignment_id=assignment.id,
    )

    for field, value in changes.items():
        setattr(assignment, field, value)

    try:
        db.commit()
        db.refresh(assignment)
        return assignment
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not update the salary component assignment",
        ) from exc
    except Exception:
        db.rollback()
        raise
