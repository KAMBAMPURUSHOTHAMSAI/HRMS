
from datetime import date, datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.compensation_history import CompensationHistory
from app.models.employee import Employee
from app.schemas.compensation_history import CompensationHistoryCreate


COMPANY_TIMEZONE = ZoneInfo("Asia/Kolkata")


def _company_today() -> date:
    return datetime.now(COMPANY_TIMEZONE).date()


def list_compensation_history(
    db: Session,
    employee_id: int,
) -> list[CompensationHistory]:
    employee = db.get(Employee, employee_id)

    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )

    query = (
        select(CompensationHistory)
        .where(CompensationHistory.employee_id == employee_id)
        .order_by(
            CompensationHistory.effective_from.desc(),
            CompensationHistory.id.desc(),
        )
    )

    return list(db.scalars(query).all())


def create_compensation_revision(
    db: Session,
    payload: CompensationHistoryCreate,
    actor_user_id: int,
) -> CompensationHistory:
    employee = db.get(Employee, payload.employee_id)

    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )

    if (
        payload.effective_to is not None
        and payload.effective_to < payload.effective_from
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="effective_to cannot be earlier than effective_from",
        )

    revisions = list(
        db.scalars(
            select(CompensationHistory)
            .where(CompensationHistory.employee_id == employee.id)
            .order_by(CompensationHistory.effective_from.asc())
        ).all()
    )

    if any(
        item.effective_from == payload.effective_from
        for item in revisions
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A salary revision already exists for this effective date",
        )

    next_revisions = [
        item
        for item in revisions
        if item.effective_from > payload.effective_from
    ]
    next_revision = (
        min(next_revisions, key=lambda item: item.effective_from)
        if next_revisions
        else None
    )

    effective_to = payload.effective_to

    if next_revision is not None:
        day_before_next = date.fromordinal(
            next_revision.effective_from.toordinal() - 1
        )

        if effective_to is None:
            effective_to = day_before_next
        elif effective_to >= next_revision.effective_from:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The salary revision overlaps a later revision",
            )

    if effective_to is not None and effective_to < payload.effective_from:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The salary revision has an invalid effective period",
        )

    # Find the salary applicable immediately before the new revision.
    day_before_new_revision = date.fromordinal(
        payload.effective_from.toordinal() - 1
    )

    previous_revision = max(
        (
            item
            for item in revisions
            if item.effective_from <= day_before_new_revision
            and (
                item.effective_to is None
                or item.effective_to >= day_before_new_revision
            )
        ),
        key=lambda item: item.effective_from,
        default=None,
    )

    if previous_revision is not None:
        previous_salary = previous_revision.new_monthly_salary
    elif payload.previous_monthly_salary is not None:
        previous_salary = payload.previous_monthly_salary
    else:
        previous_salary = employee.monthly_salary

    # Close any older revision that would overlap the new one.
    for item in revisions:
        if (
            item.effective_from < payload.effective_from
            and (
                item.effective_to is None
                or item.effective_to >= payload.effective_from
            )
        ):
            item.effective_to = day_before_new_revision

    values = payload.model_dump()
    values["previous_monthly_salary"] = previous_salary
    values["effective_to"] = effective_to

    revision = CompensationHistory(
        **values,
        revised_by_user_id=actor_user_id,
    )

    try:
        db.add(revision)
        db.flush()

        today = _company_today()

        current_revision = db.scalar(
            select(CompensationHistory)
            .where(
                CompensationHistory.employee_id == employee.id,
                CompensationHistory.effective_from <= today,
                (
                    CompensationHistory.effective_to.is_(None)
                    | (CompensationHistory.effective_to >= today)
                ),
            )
            .order_by(CompensationHistory.effective_from.desc())
            .limit(1)
        )

        # Future revisions must not change today's salary.
        if current_revision is not None:
            employee.monthly_salary = (
                current_revision.new_monthly_salary
            )

        db.commit()
        db.refresh(revision)
        return revision

    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not save the compensation revision",
        ) from exc
    except Exception:
        db.rollback()
        raise
