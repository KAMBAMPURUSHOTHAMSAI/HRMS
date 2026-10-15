
from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.permissions import require_permissions
from app.models.user import User
from app.schemas.holiday import (
    HolidayCreate,
    HolidayRead,
    HolidaySelectionRead,
    HolidayUpdate,
)
from app.services.holiday_service import (
    cancel_optional_holiday,
    create_holiday,
    deactivate_holiday,
    get_active_employee,
    list_available_holidays,
    list_holidays,
    list_my_holiday_selections,
    select_optional_holiday,
    update_holiday,
)


router = APIRouter(
    prefix="/holidays",
    tags=["Holiday Management"],
)


# Employee calendar: active company-wide and optional holidays.
@router.get(
    "/calendar",
    response_model=list[HolidayRead],
)
def read_holiday_calendar(
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permissions("HOLIDAYS.READ_SELF")
    ),
):
    employee = get_active_employee(current_user)

    # Employee.region will be added in a later step.
    # Until then, regional holidays are not assigned by guesswork.
    employee_region = getattr(employee, "region", None)

    return list_available_holidays(
        db,
        start_date=start_date,
        end_date=end_date,
        region=employee_region,
    )


# Admin/HR holiday listing, with optional filters.
@router.get(
    "",
    response_model=list[HolidayRead],
)
def read_holidays(
    start_date: date | None = None,
    end_date: date | None = None,
    holiday_type: str | None = Query(
        default=None,
        pattern="^(COMPANY|REGIONAL|OPTIONAL)$",
    ),
    region: str | None = None,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    _current_user: User = Depends(
        require_permissions("HOLIDAYS.READ_ALL")
    ),
):
    return list_holidays(
        db,
        start_date=start_date,
        end_date=end_date,
        holiday_type=holiday_type,
        region=region,
        include_inactive=include_inactive,
    )


# Employee: view own optional holiday selection history.
@router.get(
    "/me/selections",
    response_model=list[HolidaySelectionRead],
)
def read_my_holiday_selections(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permissions("HOLIDAYS.READ_SELF")
    ),
):
    return list_my_holiday_selections(db, current_user)


# Admin/HR: create a holiday.
@router.post(
    "",
    response_model=HolidayRead,
    status_code=status.HTTP_201_CREATED,
)
def add_holiday(
    payload: HolidayCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permissions("HOLIDAYS.MANAGE")
    ),
):
    return create_holiday(
        db,
        payload,
        created_by_user_id=current_user.id,
    )


# Admin/HR: update holiday details.
@router.patch(
    "/{holiday_id}",
    response_model=HolidayRead,
)
def edit_holiday(
    holiday_id: int,
    payload: HolidayUpdate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(
        require_permissions("HOLIDAYS.MANAGE")
    ),
):
    return update_holiday(db, holiday_id, payload)


# Admin/HR: deactivate without deleting historical data.
@router.delete(
    "/{holiday_id}",
    response_model=HolidayRead,
)
def remove_holiday(
    holiday_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(
        require_permissions("HOLIDAYS.MANAGE")
    ),
):
    return deactivate_holiday(db, holiday_id)


# Employee: select an optional holiday.
@router.post(
    "/{holiday_id}/select",
    response_model=HolidaySelectionRead,
    status_code=status.HTTP_201_CREATED,
)
def select_holiday(
    holiday_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permissions("HOLIDAYS.SELECT")
    ),
):
    return select_optional_holiday(
        db,
        current_user,
        holiday_id,
    )


# Employee: cancel an existing optional holiday selection.
@router.delete(
    "/{holiday_id}/select",
    response_model=HolidaySelectionRead,
)
def cancel_holiday_selection(
    holiday_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permissions("HOLIDAYS.SELECT")
    ),
):
    return cancel_optional_holiday(
        db,
        current_user,
        holiday_id,
    )
