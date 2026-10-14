from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.employee import Employee
from app.models.leave_balance import LeaveBalance
from app.models.leave_request import LeaveRequest
from app.models.leave_type import LeaveType
from app.models.user import User
from app.schemas.leave import (
    LeaveBalanceRead,
    LeaveDecision,
    LeaveRequestCreate,
    LeaveRequestRead,
)


COMPANY_TIMEZONE = ZoneInfo("Asia/Kolkata")
ZERO = Decimal("0.00")


def get_current_employee(user: User) -> Employee:
    employee = user.employee

    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile is not configured for this account",
        )

    if not user.is_active or employee.employment_status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive employees cannot apply for leave",
        )

    return employee


def working_days_by_year(
    start_date: date,
    end_date: date,
) -> dict[int, Decimal]:
    if end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="End date cannot be before start date",
        )

    result: dict[int, Decimal] = {}
    current = start_date

    while current <= end_date:
        if current.weekday() < 5:
            year = current.year
            result[year] = result.get(year, ZERO) + Decimal("1.00")

        current += timedelta(days=1)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The selected period contains no working days",
        )

    return result


def total_working_days(
    start_date: date,
    end_date: date,
) -> Decimal:
    return sum(
        working_days_by_year(start_date, end_date).values(),
        ZERO,
    )


def get_active_leave_type(
    db: Session,
    leave_type_id: int,
) -> LeaveType:
    leave_type = db.get(LeaveType, leave_type_id)

    if leave_type is None or not leave_type.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active leave type not found",
        )

    return leave_type


def get_or_create_balance(
    db: Session,
    employee_id: int,
    leave_type: LeaveType,
    year: int,
    lock: bool = False,
) -> LeaveBalance:
    statement = select(LeaveBalance).where(
        LeaveBalance.employee_id == employee_id,
        LeaveBalance.leave_type_id == leave_type.id,
        LeaveBalance.year == year,
    )

    if lock:
        statement = statement.with_for_update()

    balance = db.scalar(statement)

    if balance is None:
        balance = LeaveBalance(
            employee_id=employee_id,
            leave_type_id=leave_type.id,
            year=year,
            entitled_days=leave_type.annual_quota,
            used_days=ZERO,
        )
        db.add(balance)
        db.flush()

    return balance


def serialize_leave_request(
    request: LeaveRequest,
) -> LeaveRequestRead:
    employee = request.employee
    user = employee.user

    return LeaveRequestRead(
        id=request.id,
        employee_id=request.employee_id,
        employee_name=f"{user.first_name} {user.last_name}",
        employee_email=user.email,
        leave_type_id=request.leave_type_id,
        leave_type_name=request.leave_type.name,
        leave_type_code=request.leave_type.code,
        is_paid=request.leave_type.is_paid,
        start_date=request.start_date,
        end_date=request.end_date,
        total_days=request.total_days,
        reason=request.reason,
        status=request.status,
        approved_by_user_id=request.approved_by_user_id,
        decided_at=request.decided_at,
        decision_note=request.decision_note,
        created_at=request.created_at,
    )


def serialize_leave_balance(
    balance: LeaveBalance,
) -> LeaveBalanceRead:
    return LeaveBalanceRead(
        employee_id=balance.employee_id,
        leave_type_id=balance.leave_type_id,
        leave_type_name=balance.leave_type.name,
        leave_type_code=balance.leave_type.code,
        year=balance.year,
        entitled_days=balance.entitled_days,
        used_days=balance.used_days,
        available_days=balance.entitled_days - balance.used_days,
        is_paid=balance.leave_type.is_paid,
    )


def get_request_query():
    return (
        select(LeaveRequest)
        .options(
            selectinload(LeaveRequest.leave_type),
            selectinload(LeaveRequest.employee).selectinload(Employee.user),
        )
    )


def get_leave_request(
    db: Session,
    request_id: int,
) -> LeaveRequest:
    request = db.scalar(
        get_request_query().where(LeaveRequest.id == request_id)
    )

    if request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Leave request not found",
        )

    return request


def apply_leave(
    db: Session,
    user: User,
    payload: LeaveRequestCreate,
) -> LeaveRequestRead:
    employee = get_current_employee(user)
    leave_type = get_active_leave_type(db, payload.leave_type_id)

    if payload.end_date < payload.start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="End date cannot be before start date",
        )

    days_by_year = working_days_by_year(
        payload.start_date,
        payload.end_date,
    )

    overlapping = db.scalar(
        select(LeaveRequest.id).where(
            LeaveRequest.employee_id == employee.id,
            LeaveRequest.status.in_(["PENDING", "APPROVED"]),
            LeaveRequest.start_date <= payload.end_date,
            LeaveRequest.end_date >= payload.start_date,
        ).limit(1)
    )

    if overlapping is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This leave period overlaps with an existing request",
        )

    if leave_type.is_paid:
        for year, requested_days in days_by_year.items():
            balance = get_or_create_balance(
                db,
                employee.id,
                leave_type,
                year,
            )

            available = balance.entitled_days - balance.used_days

            if requested_days > available:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Insufficient {leave_type.name} balance "
                        f"for {year}. Available: {available} days"
                    ),
                )

    request = LeaveRequest(
        employee_id=employee.id,
        leave_type_id=leave_type.id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        total_days=sum(days_by_year.values(), ZERO),
        reason=payload.reason,
        status="PENDING",
    )

    try:
        db.add(request)
        db.commit()
        return serialize_leave_request(
            get_leave_request(db, request.id)
        )
    except Exception:
        db.rollback()
        raise


def list_my_leave_requests(
    db: Session,
    user: User,
) -> list[LeaveRequestRead]:
    employee = get_current_employee(user)

    requests = db.scalars(
        get_request_query()
        .where(LeaveRequest.employee_id == employee.id)
        .order_by(LeaveRequest.created_at.desc())
    ).all()

    return [serialize_leave_request(item) for item in requests]


def list_leave_requests(
    db: Session,
    employee_id: int | None = None,
    department_id: int | None = None,
    leave_status: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[LeaveRequestRead]:
    statement = get_request_query().join(
        Employee,
        LeaveRequest.employee_id == Employee.id,
    )

    if employee_id is not None:
        statement = statement.where(
            LeaveRequest.employee_id == employee_id
        )

    if department_id is not None:
        statement = statement.where(
            Employee.department_id == department_id
        )

    if leave_status is not None:
        statement = statement.where(
            LeaveRequest.status == leave_status
        )

    if start_date is not None:
        statement = statement.where(
            LeaveRequest.end_date >= start_date
        )

    if end_date is not None:
        statement = statement.where(
            LeaveRequest.start_date <= end_date
        )

    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="start_date cannot be after end_date",
        )

    statement = (
        statement
        .order_by(LeaveRequest.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    requests = db.scalars(statement).all()

    return [serialize_leave_request(item) for item in requests]


def list_my_leave_balances(
    db: Session,
    user: User,
    year: int,
) -> list[LeaveBalanceRead]:
    employee = get_current_employee(user)

    paid_types = db.scalars(
        select(LeaveType).where(
            LeaveType.is_active.is_(True),
            LeaveType.is_paid.is_(True),
        )
    ).all()

    for leave_type in paid_types:
        get_or_create_balance(
            db,
            employee.id,
            leave_type,
            year,
        )

    db.commit()

    balances = db.scalars(
        select(LeaveBalance)
        .options(selectinload(LeaveBalance.leave_type))
        .where(
            LeaveBalance.employee_id == employee.id,
            LeaveBalance.year == year,
        )
        .order_by(LeaveBalance.leave_type_id)
    ).all()

    return [
        serialize_leave_balance(balance)
        for balance in balances
        if balance.leave_type.is_paid
    ]


def decide_leave_request(
    db: Session,
    request_id: int,
    decision: LeaveDecision,
    approver: User,
    approve: bool,
) -> LeaveRequestRead:
    request = db.scalar(
        select(LeaveRequest)
        .where(LeaveRequest.id == request_id)
        .with_for_update()
    )

    if request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Leave request not found",
        )

    if request.status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only pending leave requests can be decided",
        )

    try:
        if approve:
            leave_type = db.get(LeaveType, request.leave_type_id)

            if leave_type is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Leave type not found",
                )

            if leave_type.is_paid:
                employee = db.get(Employee, request.employee_id)

                days_by_year = working_days_by_year(
                    request.start_date,
                    request.end_date,
                )

                for year, days in days_by_year.items():
                    balance = get_or_create_balance(
                        db,
                        employee.id,
                        leave_type,
                        year,
                        lock=True,
                    )

                    available = (
                        balance.entitled_days - balance.used_days
                    )

                    if days > available:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail=(
                                f"Insufficient {leave_type.name} balance "
                                f"for {year} at approval time"
                            ),
                        )

                    balance.used_days += days

            request.status = "APPROVED"
        else:
            request.status = "REJECTED"

        request.approved_by_user_id = approver.id
        request.decided_at = datetime.now(COMPANY_TIMEZONE)
        request.decision_note = (
            decision.decision_note.strip()
            if decision.decision_note
            else None
        )

        db.commit()

        return serialize_leave_request(
            get_leave_request(db, request_id)
        )

    except Exception:
        db.rollback()
        raise