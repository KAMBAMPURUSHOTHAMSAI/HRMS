
from datetime import date, datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.holiday import Holiday
from app.models.holiday_selection import HolidaySelection
from app.models.user import User
from app.schemas.holiday import HolidayCreate, HolidayUpdate


COMPANY_TIMEZONE = ZoneInfo("Asia/Kolkata")


def get_active_employee(user: User) -> Employee:
    """Return the employee linked to the authenticated user."""
    employee = user.employee

    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile is not configured for this account",
        )

    if not user.is_active or employee.employment_status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive employees cannot manage holiday selections",
        )

    return employee


def _validate_date_range(
    start_date: date | None,
    end_date: date | None,
) -> None:
    if (
        start_date is not None
        and end_date is not None
        and start_date > end_date
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="start_date cannot be after end_date",
        )


def list_holidays(
    db: Session,
    start_date: date | None = None,
    end_date: date | None = None,
    holiday_type: str | None = None,
    region: str | None = None,
    include_inactive: bool = False,
) -> list[Holiday]:
    """List holidays with optional date, type and region filters."""
    _validate_date_range(start_date, end_date)

    statement = select(Holiday)

    if not include_inactive:
        statement = statement.where(Holiday.is_active.is_(True))

    if start_date is not None:
        statement = statement.where(
            Holiday.holiday_date >= start_date
        )

    if end_date is not None:
        statement = statement.where(
            Holiday.holiday_date <= end_date
        )

    if holiday_type is not None:
        statement = statement.where(
            Holiday.holiday_type == holiday_type
        )

    if region is not None:
        statement = statement.where(
            or_(
                Holiday.holiday_type != "REGIONAL",
                Holiday.region == region.strip(),
            )
        )

    statement = statement.order_by(
        Holiday.holiday_date,
        Holiday.name,
    )

    return list(db.scalars(statement).all())


def list_available_holidays(
    db: Session,
    start_date: date | None = None,
    end_date: date | None = None,
    region: str | None = None,
) -> list[Holiday]:
    """List active holidays visible to an employee in a region."""
    _validate_date_range(start_date, end_date)

    statement = select(Holiday).where(
        Holiday.is_active.is_(True),
        or_(
            Holiday.holiday_type != "REGIONAL",
            (
                Holiday.region == region.strip()
                if region and region.strip()
                else False
            ),
        ),
    )

    if start_date is not None:
        statement = statement.where(
            Holiday.holiday_date >= start_date
        )

    if end_date is not None:
        statement = statement.where(
            Holiday.holiday_date <= end_date
        )

    statement = statement.order_by(
        Holiday.holiday_date,
        Holiday.name,
    )

    return list(db.scalars(statement).all())


def create_holiday(
    db: Session,
    payload: HolidayCreate,
    created_by_user_id: int,
) -> Holiday:
    """Create a holiday. Authorization belongs in the API endpoint."""
    holiday = Holiday(
        **payload.model_dump(),
        created_by_user_id=created_by_user_id,
    )

    db.add(holiday)

    try:
        db.commit()
        db.refresh(holiday)
        return holiday
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The holiday could not be saved because of a data conflict",
        ) from None


def update_holiday(
    db: Session,
    holiday_id: int,
    payload: HolidayUpdate,
) -> Holiday:
    """Update holiday data without replacing the existing record."""
    holiday = db.get(Holiday, holiday_id)

    if holiday is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Holiday not found",
        )

    changes = payload.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least one field to update",
        )

    new_type = changes.get(
        "holiday_type",
        holiday.holiday_type,
    )
    new_region = changes.get(
        "region",
        holiday.region,
    )

    if new_type == "REGIONAL" and not new_region:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Region is required for regional holidays",
        )

    if new_type != "REGIONAL":
        if changes.get("region"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Only regional holidays can have a region",
            )

        changes["region"] = None

    for field, value in changes.items():
        setattr(holiday, field, value)

    try:
        db.commit()
        db.refresh(holiday)
        return holiday
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The holiday update conflicts with database constraints",
        ) from None


def deactivate_holiday(
    db: Session,
    holiday_id: int,
) -> Holiday:
    """Deactivate a holiday while preserving its history."""
    holiday = db.get(Holiday, holiday_id)

    if holiday is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Holiday not found",
        )

    holiday.is_active = False

    db.commit()
    db.refresh(holiday)

    return holiday


def select_optional_holiday(
    db: Session,
    user: User,
    holiday_id: int,
) -> HolidaySelection:
    """Select an active optional holiday for the current employee."""
    employee = get_active_employee(user)
    holiday = db.get(Holiday, holiday_id)

    if (
        holiday is None
        or not holiday.is_active
        or holiday.holiday_type != "OPTIONAL"
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active optional holiday not found",
        )

    existing = db.scalar(
        select(HolidaySelection).where(
            HolidaySelection.employee_id == employee.id,
            HolidaySelection.holiday_id == holiday_id,
        )
    )

    if existing is not None:
        if existing.status == "SELECTED":
            return existing

        existing.status = "SELECTED"
        existing.selected_at = datetime.now(COMPANY_TIMEZONE)
        selection = existing
    else:
        selection = HolidaySelection(
            employee_id=employee.id,
            holiday_id=holiday_id,
            status="SELECTED",
        )
        db.add(selection)

    try:
        db.commit()
        db.refresh(selection)
        return selection
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The optional holiday selection could not be saved",
        ) from None


def cancel_optional_holiday(
    db: Session,
    user: User,
    holiday_id: int,
) -> HolidaySelection:
    """Cancel the current employee's optional holiday selection."""
    employee = get_active_employee(user)

    selection = db.scalar(
        select(HolidaySelection).where(
            HolidaySelection.employee_id == employee.id,
            HolidaySelection.holiday_id == holiday_id,
            HolidaySelection.status == "SELECTED",
        )
    )

    if selection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active optional holiday selection not found",
        )

    selection.status = "CANCELLED"

    db.commit()
    db.refresh(selection)

    return selection


def list_my_holiday_selections(
    db: Session,
    user: User,
) -> list[HolidaySelection]:
    """Return the current employee's selection history."""
    employee = get_active_employee(user)

    statement = (
        select(HolidaySelection)
        .where(HolidaySelection.employee_id == employee.id)
        .order_by(HolidaySelection.created_at.desc())
    )

    return list(db.scalars(statement).all())
