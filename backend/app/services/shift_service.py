
from datetime import date, timedelta

from fastapi import HTTPException, status
from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.department import Department
from app.models.employee import Employee
from app.models.shift import Shift
from app.models.shift_assignment import ShiftAssignment
from app.schemas.shift import (
    ShiftAssignmentCreate,
    ShiftCreate,
    ShiftUpdate,
)


def _validate_shift_configuration(
    shift_type: str,
    start_time,
    end_time,
) -> None:
    """Validate timing rules for fixed and overnight shifts."""
    if shift_type not in {
        "GENERAL",
        "NIGHT",
        "FLEXIBLE",
        "REMOTE",
    }:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unsupported shift type",
        )

    if shift_type in {"GENERAL", "NIGHT"}:
        if start_time is None or end_time is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Start and end times are required for this shift type",
            )

        if start_time == end_time:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Shift start and end times cannot be identical",
            )

        if shift_type == "GENERAL" and end_time <= start_time:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="General shift end time must be after start time",
            )


def _get_shift_or_404(
    db: Session,
    shift_id: int,
) -> Shift:
    shift = db.get(Shift, shift_id)

    if shift is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shift not found",
        )

    return shift


def list_shifts(
    db: Session,
    include_inactive: bool = False,
) -> list[Shift]:
    """List configured shifts."""
    statement = select(Shift)

    if not include_inactive:
        statement = statement.where(
            Shift.is_active.is_(True)
        )

    statement = statement.order_by(Shift.name)

    return list(db.scalars(statement).all())


def create_shift(
    db: Session,
    payload: ShiftCreate,
    created_by_user_id: int,
) -> Shift:
    """Create a shift after validating timing configuration."""
    name = payload.name.strip()

    if not name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Shift name cannot be empty",
        )

    _validate_shift_configuration(
        payload.shift_type,
        payload.start_time,
        payload.end_time,
    )

    existing = db.scalar(
        select(Shift).where(
            Shift.name == name
        )
    )

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A shift with this name already exists",
        )

    shift = Shift(
        **payload.model_dump(exclude={"name"}),
        name=name,
        created_by_user_id=created_by_user_id,
    )

    db.add(shift)

    try:
        db.commit()
        db.refresh(shift)
        return shift
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to create shift because of a data conflict",
        ) from None


def update_shift(
    db: Session,
    shift_id: int,
    payload: ShiftUpdate,
) -> Shift:
    """Update shift configuration without deleting its history."""
    shift = _get_shift_or_404(db, shift_id)
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
                detail="Shift name cannot be empty",
            )

        changes["name"] = changes["name"].strip()

        duplicate = db.scalar(
            select(Shift).where(
                Shift.name == changes["name"],
                Shift.id != shift_id,
            )
        )

        if duplicate is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Another shift already uses this name",
            )

    new_type = changes.get("shift_type", shift.shift_type)
    new_start = changes.get("start_time", shift.start_time)
    new_end = changes.get("end_time", shift.end_time)

    _validate_shift_configuration(
        new_type,
        new_start,
        new_end,
    )

    for field, value in changes.items():
        setattr(shift, field, value)

    try:
        db.commit()
        db.refresh(shift)
        return shift
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to update shift because of a data conflict",
        ) from None


def deactivate_shift(
    db: Session,
    shift_id: int,
) -> Shift:
    """
    Deactivate a shift while retaining its records and assignments.
    Historical assignments remain available for reporting.
    """
    shift = _get_shift_or_404(db, shift_id)

    shift.is_active = False

    try:
        db.commit()
        db.refresh(shift)
        return shift
    except Exception:
        db.rollback()
        raise


def _validate_assignment_target(
    db: Session,
    payload: ShiftAssignmentCreate,
) -> None:
    """Validate the selected employee or department."""
    if payload.employee_id is not None:
        employee = db.get(Employee, payload.employee_id)

        if employee is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee not found",
            )

        if employee.employment_status != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A shift cannot be assigned to an inactive employee",
            )

    elif payload.department_id is not None:
        department = db.get(
            Department,
            payload.department_id,
        )

        if department is None or not department.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Active department not found",
            )


def _get_target_assignments(
    db: Session,
    payload: ShiftAssignmentCreate,
) -> list[ShiftAssignment]:
    """Lock and return assignments for the same target only."""
    statement = select(ShiftAssignment)

    if payload.employee_id is not None:
        statement = statement.where(
            ShiftAssignment.employee_id == payload.employee_id
        )
    else:
        statement = statement.where(
            ShiftAssignment.department_id == payload.department_id
        )

    statement = (
        statement
        .order_by(ShiftAssignment.effective_from)
        .with_for_update()
    )

    return list(db.scalars(statement).all())


def assign_shift(
    db: Session,
    payload: ShiftAssignmentCreate,
    assigned_by_user_id: int,
) -> ShiftAssignment:
    """
    Assign a shift to one employee or one department.

    For an open-ended new assignment, an earlier overlapping assignment
    for the same target is closed on the preceding day. Overlapping future
    assignments are rejected instead of silently rewriting history.
    """
    shift = _get_shift_or_404(db, payload.shift_id)

    if not shift.is_active:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Inactive shifts cannot receive new assignments",
        )

    if (
        payload.effective_to is not None
        and payload.effective_to < payload.effective_from
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Assignment end date cannot precede its start date",
        )

    _validate_assignment_target(db, payload)

    existing_assignments = _get_target_assignments(db, payload)

    requested_end = payload.effective_to or date.max

    overlapping = [
        item
        for item in existing_assignments
        if (
            item.effective_from <= requested_end
            and (
                item.effective_to is None
                or item.effective_to >= payload.effective_from
            )
        )
    ]

    if overlapping:
        # Automatically close earlier overlapping assignments only when
        # the new assignment continues indefinitely.
        can_close_previous = (
            payload.effective_to is None
            and all(
                item.effective_from < payload.effective_from
                for item in overlapping
            )
        )

        if not can_close_previous:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "The assignment overlaps an existing assignment "
                    "for this employee or department. Resolve the "
                    "conflicting date range first."
                ),
            )

        previous_end = payload.effective_from - timedelta(days=1)

        for previous in overlapping:
            previous.effective_to = previous_end

    assignment = ShiftAssignment(
        shift_id=payload.shift_id,
        employee_id=payload.employee_id,
        department_id=payload.department_id,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
        assigned_by_user_id=assigned_by_user_id,
    )

    db.add(assignment)

    try:
        db.commit()
        db.refresh(assignment)
        return assignment
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to create shift assignment",
        ) from None


def list_shift_assignments(
    db: Session,
    employee_id: int | None = None,
    department_id: int | None = None,
    include_history: bool = True,
) -> list[ShiftAssignment]:
    """List shift assignment history with optional target filters."""
    if employee_id is not None and department_id is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Filter by employee or department, not both",
        )

    statement = select(ShiftAssignment)

    if employee_id is not None:
        statement = statement.where(
            ShiftAssignment.employee_id == employee_id
        )

    if department_id is not None:
        statement = statement.where(
            ShiftAssignment.department_id == department_id
        )

    if not include_history:
        today = date.today()

        statement = statement.where(
            ShiftAssignment.effective_from <= today,
            or_(
                ShiftAssignment.effective_to.is_(None),
                ShiftAssignment.effective_to >= today,
            ),
        )

    statement = statement.order_by(
        ShiftAssignment.effective_from.desc(),
        ShiftAssignment.id.desc(),
    )

    return list(db.scalars(statement).all())


def resolve_employee_shift(
    db: Session,
    employee_id: int,
    on_date: date,
) -> tuple[ShiftAssignment, Shift] | None:
    """
    Resolve the applicable shift on a particular date.

    Employee-specific assignment takes priority over department-level
    assignment. Among matching assignments, the latest effective_from
    takes precedence.
    """
    employee = db.get(Employee, employee_id)

    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )

    def find_assignment(
        employee_target: int | None,
        department_target: int | None,
    ) -> ShiftAssignment | None:
        statement = select(ShiftAssignment).where(
            ShiftAssignment.effective_from <= on_date,
            or_(
                ShiftAssignment.effective_to.is_(None),
                ShiftAssignment.effective_to >= on_date,
            ),
        )

        if employee_target is not None:
            statement = statement.where(
                ShiftAssignment.employee_id == employee_target,
                ShiftAssignment.department_id.is_(None),
            )
        else:
            statement = statement.where(
                ShiftAssignment.employee_id.is_(None),
                ShiftAssignment.department_id == department_target,
            )

        statement = (
            statement
            .order_by(
                ShiftAssignment.effective_from.desc(),
                ShiftAssignment.id.desc(),
            )
            .limit(1)
        )

        return db.scalar(statement)

    assignment = find_assignment(
        employee_target=employee.id,
        department_target=None,
    )

    if assignment is None:
        assignment = find_assignment(
            employee_target=None,
            department_target=employee.department_id,
        )

    if assignment is None:
        return None

    shift = db.get(Shift, assignment.shift_id)

    if shift is None:
        return None

    return assignment, shift
