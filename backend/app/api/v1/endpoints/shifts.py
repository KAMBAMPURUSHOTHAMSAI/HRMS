
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.permissions import require_permissions
from app.models.user import User
from app.schemas.shift import (
    ShiftAssignmentCreate,
    ShiftAssignmentRead,
    ShiftAttendanceReport,
    ShiftCreate,
    ShiftRead,
    ShiftUpdate,
)
from app.services.shift_service import (
    assign_shift,
    create_shift,
    deactivate_shift,
    list_shift_assignments,
    list_shifts,
    update_shift,
)
from app.services.shift_report_service import (
    get_shift_attendance_report,
)


router = APIRouter(
    prefix="/shifts",
    tags=["Shift Management"],
)


# ---------------------------------------------------------
# Shift configuration
# ---------------------------------------------------------

@router.get(
    "",
    response_model=list[ShiftRead],
)
def read_shifts(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permissions("SHIFTS.READ")
    ),
):
    if include_inactive:
        active_roles = {
            association.role.name
            for association in current_user.user_roles
            if association.role and association.role.is_active
        }

        if not active_roles.intersection({"ADMIN", "HR"}):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot view inactive shifts",
            )

    return list_shifts(
        db,
        include_inactive=include_inactive,
    )


@router.post(
    "",
    response_model=ShiftRead,
    status_code=status.HTTP_201_CREATED,
)
def add_shift(
    payload: ShiftCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permissions("SHIFTS.MANAGE")
    ),
):
    return create_shift(
        db,
        payload,
        created_by_user_id=current_user.id,
    )


@router.patch(
    "/{shift_id}",
    response_model=ShiftRead,
)
def edit_shift(
    shift_id: int,
    payload: ShiftUpdate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(
        require_permissions("SHIFTS.MANAGE")
    ),
):
    return update_shift(
        db,
        shift_id,
        payload,
    )


@router.delete(
    "/{shift_id}",
    response_model=ShiftRead,
)
def remove_shift(
    shift_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(
        require_permissions("SHIFTS.MANAGE")
    ),
):
    return deactivate_shift(
        db,
        shift_id,
    )


# ---------------------------------------------------------
# Shift assignments and history
# ---------------------------------------------------------

@router.get(
    "/assignments",
    response_model=list[ShiftAssignmentRead],
)
def read_shift_assignments(
    employee_id: int | None = Query(default=None, gt=0),
    department_id: int | None = Query(default=None, gt=0),
    include_history: bool = True,
    db: Session = Depends(get_db),
    _current_user: User = Depends(
        require_permissions("SHIFTS.READ")
    ),
):
    return list_shift_assignments(
        db,
        employee_id=employee_id,
        department_id=department_id,
        include_history=include_history,
    )


@router.post(
    "/assignments",
    response_model=ShiftAssignmentRead,
    status_code=status.HTTP_201_CREATED,
)
def add_shift_assignment(
    payload: ShiftAssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permissions("SHIFTS.ASSIGN")
    ),
):
    return assign_shift(
        db,
        payload,
        assigned_by_user_id=current_user.id,
    )


# ---------------------------------------------------------
# Shift-wise attendance report
# ---------------------------------------------------------

@router.get(
    "/reports/attendance",
    response_model=ShiftAttendanceReport,
)
def read_shift_attendance_report(
    start_date: date,
    end_date: date,
    employee_id: int | None = Query(default=None, gt=0),
    department_id: int | None = Query(default=None, gt=0),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=500),
    db: Session = Depends(get_db),
    _current_user: User = Depends(
        require_permissions("SHIFTS.READ")
    ),
):
    return get_shift_attendance_report(
        db=db,
        start_date=start_date,
        end_date=end_date,
        employee_id=employee_id,
        department_id=department_id,
        skip=skip,
        limit=limit,
    )
