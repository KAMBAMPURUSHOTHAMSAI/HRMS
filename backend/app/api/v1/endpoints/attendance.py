
from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.permissions import require_permissions
from app.models.user import User
from app.schemas.attendance import (
    AttendanceCorrection,
    AttendanceRead,
    AttendanceSummary,
)
from app.services.attendance_service import (
    check_in,
    check_out,
    correct_attendance,
    get_my_attendance,
    get_my_monthly_summary,
    list_all_attendance,
)


router = APIRouter(
    prefix="/attendance",
    tags=["Attendance"],
)


@router.post(
    "/check-in",
    response_model=AttendanceRead,
    status_code=status.HTTP_201_CREATED,
)
def employee_check_in(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permissions("ATTENDANCE.CHECK_IN")
    ),
):
    return check_in(db, current_user)


@router.post(
    "/check-out",
    response_model=AttendanceRead,
)
def employee_check_out(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permissions("ATTENDANCE.CHECK_OUT")
    ),
):
    return check_out(db, current_user)


@router.get(
    "/me",
    response_model=list[AttendanceRead],
)
def read_my_attendance(
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permissions("ATTENDANCE.READ_SELF")
    ),
):
    return get_my_attendance(
        db,
        current_user,
        start_date,
        end_date,
    )


@router.get(
    "/me/summary",
    response_model=AttendanceSummary,
)
def read_my_monthly_summary(
    year: int = Query(ge=2000, le=2100),
    month: int = Query(ge=1, le=12),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permissions("ATTENDANCE.READ_SELF")
    ),
):
    return get_my_monthly_summary(
        db,
        current_user,
        year,
        month,
    )


@router.get(
    "",
    response_model=list[AttendanceRead],
    dependencies=[
        Depends(require_permissions("ATTENDANCE.READ_ALL"))
    ],
)
def read_all_attendance(
    employee_id: int | None = Query(default=None, gt=0),
    department_id: int | None = Query(default=None, gt=0),
    start_date: date | None = None,
    end_date: date | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return list_all_attendance(
        db=db,
        employee_id=employee_id,
        department_id=department_id,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit,
    )


@router.patch(
    "/{attendance_id}/correction",
    response_model=AttendanceRead,
)
def admin_correct_attendance(
    attendance_id: int,
    payload: AttendanceCorrection,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permissions("ATTENDANCE.CORRECT")
    ),
):
    return correct_attendance(
        db,
        attendance_id,
        payload,
        current_user,
    )
