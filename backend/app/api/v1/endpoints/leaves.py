
import logging
from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.core.permissions import require_permissions
from app.models.employee import Employee
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.schemas.leave import (
    LeaveBalanceRead,
    LeaveDecision,
    LeaveRequestCreate,
    LeaveRequestRead,
)
from app.services.leave_service import (
    apply_leave,
    decide_leave_request,
    get_leave_request,
    list_leave_requests,
    list_my_leave_balances,
    list_my_leave_requests,
    serialize_leave_request,
)
from app.services.notification_service import publish_user_event


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/leaves",
    tags=["Leave Management"],
)


def _send_event_safely(
    db: Session,
    background_tasks: BackgroundTasks,
    **event_data,
) -> None:
    """Do not undo a successful leave action if notification queuing fails."""
    try:
        publish_user_event(
            db=db,
            background_tasks=background_tasks,
            **event_data,
        )
    except Exception:
        logger.exception(
            "Could not queue leave notification: %s",
            event_data.get("event_type"),
        )


def _leave_email_context(leave: LeaveRequestRead) -> dict:
    return {
        "employee_name": leave.employee_name,
        "employee_email": leave.employee_email,
        "leave_type_name": leave.leave_type_name,
        "start_date": leave.start_date.isoformat(),
        "end_date": leave.end_date.isoformat(),
        "total_days": str(leave.total_days),
        "reason": leave.reason,
        "status": leave.status,
        "decision_note": leave.decision_note,
    }


def _notify_leave_application(
    db: Session,
    background_tasks: BackgroundTasks,
    leave: LeaveRequestRead,
    employee_user_id: int,
) -> None:
    context = _leave_email_context(leave)
    base_url = getattr(
        settings,
        "frontend_base_url",
        "http://localhost:5174",
    ).rstrip("/")

    # Confirmation email and in-app notification for the employee.
    _send_event_safely(
        db,
        background_tasks,
        user_id=employee_user_id,
        event_type="LEAVE_APPLIED",
        title="Leave application submitted",
        message=(
            f"Your {leave.leave_type_name} request for "
            f"{leave.start_date} to {leave.end_date} "
            "has been submitted for approval."
        ),
        email_subject="HRMS: Leave application submitted",
        template_name="leave_applied.html",
        context_data=context,
        extra_data={
            "leave_request_id": leave.id,
            "leave_status": leave.status,
        },
    )

    # Notify active ADMIN/HR users who can review leave requests.
    reviewer_ids = list(
        db.scalars(
            select(User.id)
            .join(UserRole, UserRole.user_id == User.id)
            .join(Role, Role.id == UserRole.role_id)
            .where(
                User.is_active.is_(True),
                Role.is_active.is_(True),
                Role.name.in_(["ADMIN", "HR"]),
            )
            .distinct()
        ).all()
    )

    for reviewer_id in reviewer_ids:
        _send_event_safely(
            db,
            background_tasks,
            user_id=reviewer_id,
            event_type="LEAVE_REQUIRES_REVIEW",
            title="Leave request needs review",
            message=(
                f"{leave.employee_name} submitted a "
                f"{leave.leave_type_name} request "
                f"for {leave.start_date} to {leave.end_date}."
            ),
            email_subject="HRMS: Leave request awaiting review",
            template_name="leave_for_review.html",
            context_data={
                **context,
                "review_url": f"{base_url}/admin/leaves",
            },
            extra_data={
                "leave_request_id": leave.id,
                "employee_id": leave.employee_id,
            },
        )


def _notify_leave_decision(
    db: Session,
    background_tasks: BackgroundTasks,
    leave: LeaveRequestRead,
) -> None:
    # Resolve the actual account belonging to this employee.
    employee_user_id = db.scalar(
        select(User.id).join(
            Employee,
            Employee.user_id == User.id,
        ).where(Employee.id == leave.employee_id)
    )

    if employee_user_id is None:
        logger.warning(
            "Leave request %s was decided, but its employee account "
            "could not be found for notification.",
            leave.id,
        )
        return

    approved = leave.status == "APPROVED"
    decision_word = "approved" if approved else "rejected"

    _send_event_safely(
        db,
        background_tasks,
        user_id=employee_user_id,
        event_type=f"LEAVE_{leave.status}",
        title=f"Leave request {decision_word}",
        message=(
            f"Your {leave.leave_type_name} request "
            f"for {leave.start_date} to {leave.end_date} "
            f"has been {decision_word}."
        ),
        email_subject=f"HRMS: Leave request {decision_word}",
        template_name="leave_status.html",
        context_data=_leave_email_context(leave),
        extra_data={
            "leave_request_id": leave.id,
            "leave_status": leave.status,
            "decision_note": leave.decision_note,
        },
    )


def _permission_codes(user: User) -> set[str]:
    codes = set()

    for assignment in user.user_roles:
        role = assignment.role

        if role is None or not role.is_active:
            continue

        for role_permission in role.role_permissions:
            permission = role_permission.permission

            if permission is not None:
                codes.add(permission.code.upper())

    return codes


@router.post(
    "",
    response_model=LeaveRequestRead,
    status_code=status.HTTP_201_CREATED,
)
def create_leave_application(
    payload: LeaveRequestCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permissions("LEAVES.APPLY")
    ),
):
    leave = apply_leave(db, current_user, payload)

    _notify_leave_application(
        db,
        background_tasks,
        leave,
        current_user.id,
    )

    return leave


@router.get(
    "/me",
    response_model=list[LeaveRequestRead],
)
def read_my_leave_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permissions("LEAVES.READ_SELF")
    ),
):
    return list_my_leave_requests(db, current_user)


@router.get(
    "/me/balances",
    response_model=list[LeaveBalanceRead],
)
def read_my_leave_balances(
    year: int = Query(
        default_factory=lambda: date.today().year,
        ge=2000,
        le=2100,
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permissions("LEAVES.READ_BALANCES_SELF")
    ),
):
    return list_my_leave_balances(db, current_user, year)


@router.get(
    "",
    response_model=list[LeaveRequestRead],
    dependencies=[
        Depends(require_permissions("LEAVES.READ_ALL"))
    ],
)
def read_all_leave_requests(
    employee_id: int | None = Query(default=None, gt=0),
    department_id: int | None = Query(default=None, gt=0),
    leave_status: str | None = Query(
        default=None,
        pattern="^(PENDING|APPROVED|REJECTED|CANCELLED)$",
    ),
    start_date: date | None = None,
    end_date: date | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return list_leave_requests(
        db=db,
        employee_id=employee_id,
        department_id=department_id,
        leave_status=leave_status,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{request_id}",
    response_model=LeaveRequestRead,
)
def read_leave_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    request = get_leave_request(db, request_id)
    permissions = _permission_codes(current_user)

    is_owner = request.employee.user_id == current_user.id

    if is_owner and "LEAVES.READ_SELF" in permissions:
        return serialize_leave_request(request)

    if "LEAVES.READ_ALL" in permissions:
        return serialize_leave_request(request)

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You cannot view this leave request.",
    )


@router.post(
    "/{request_id}/approve",
    response_model=LeaveRequestRead,
)
def approve_leave_request(
    request_id: int,
    payload: LeaveDecision,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permissions("LEAVES.APPROVE")
    ),
):
    leave = decide_leave_request(
        db,
        request_id,
        payload,
        current_user,
        approve=True,
    )

    _notify_leave_decision(db, background_tasks, leave)

    return leave


@router.post(
    "/{request_id}/reject",
    response_model=LeaveRequestRead,
)
def reject_leave_request(
    request_id: int,
    payload: LeaveDecision,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permissions("LEAVES.REJECT")
    ),
):
    leave = decide_leave_request(
        db,
        request_id,
        payload,
        current_user,
        approve=False,
    )

    _notify_leave_decision(db, background_tasks, leave)

    return leave
