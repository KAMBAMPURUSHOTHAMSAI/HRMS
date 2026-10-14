
import logging
from calendar import month_name

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.core.permissions import require_permissions
from app.models.employee import Employee
from app.models.email_log import EmailDeliveryLog
from app.models.payroll_record import PayrollRecord
from app.models.salary_slip import SalarySlip
from app.models.user import User
from app.schemas.salary_slip import SalarySlipRead
from app.services.notification_service import publish_user_event
from app.services.salary_slip_service import (
    generate_salary_slips,
    get_salary_slip,
    get_salary_slip_file,
    list_my_salary_slips,
    list_salary_slips,
    serialize_salary_slip,
)


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/salary-slips",
    tags=["Salary Slips"],
)


def has_privileged_role(user: User) -> bool:
    roles = {
        item.role.name
        for item in user.user_roles
        if item.role and item.role.is_active
    }
    return bool(roles.intersection({"ADMIN", "HR"}))


def _email_event_exists(
    db: Session,
    user_id: int,
    event_type: str,
    correlation_key: str,
    correlation_value: int,
) -> bool:
    """Check whether an event has already been queued for this record."""

    logs = db.scalars(
        select(EmailDeliveryLog).where(
            EmailDeliveryLog.user_id == user_id,
            EmailDeliveryLog.event_type == event_type,
        )
    ).all()

    return any(
        str(
            (log.email_context or {}).get(correlation_key, "")
        )
        == str(correlation_value)
        for log in logs
    )


def _queue_salary_event_safely(
    db: Session,
    background_tasks: BackgroundTasks,
    **event_data,
) -> None:
    """Do not undo a completed salary-slip operation if notification queuing fails."""

    try:
        publish_user_event(
            db=db,
            background_tasks=background_tasks,
            **event_data,
        )
    except Exception:
        logger.exception(
            "Could not queue salary notification: %s",
            event_data.get("event_type"),
        )


@router.post(
    "/payroll-runs/{run_id}/generate",
    response_model=list[SalarySlipRead],
    status_code=status.HTTP_201_CREATED,
)
def generate_slips(
    run_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permissions("SALARY_SLIPS.GENERATE")
    ),
):
    # Generate the PDF files and database records first.
    # The service reuses an existing salary slip when appropriate.
    slips = generate_salary_slips(
        db,
        run_id,
        current_user,
    )

    base_url = getattr(
        settings,
        "frontend_base_url",
        "http://localhost:5174",
    ).rstrip("/")

    # Reload slip records with all relationships required by the
    # notification templates and recipient lookup.
    slip_ids = [slip.id for slip in slips if slip.id is not None]

    if slip_ids:
        loaded_slips = db.scalars(
            select(SalarySlip)
            .where(SalarySlip.id.in_(slip_ids))
            .options(
                selectinload(SalarySlip.payroll_record)
                .selectinload(PayrollRecord.employee)
                .selectinload(Employee.user),
                selectinload(SalarySlip.payroll_record)
                .selectinload(PayrollRecord.payroll_run),
            )
        ).all()
    else:
        loaded_slips = []

    for slip in loaded_slips:
        record = slip.payroll_record
        employee = record.employee if record else None
        user = employee.user if employee else None
        payroll_run = record.payroll_run if record else None

        if (
            user is None
            or not user.is_active
            or payroll_run is None
        ):
            continue

        employee_name = " ".join(
            part
            for part in (user.first_name, user.last_name)
            if part
        )

        month_label = month_name[payroll_run.month]

        # Backfill a missing payroll-processed event for a previously
        # simulated payroll, without issuing another simulated credit.
        if (
            record.credit_status == "SIMULATED"
            and not _email_event_exists(
                db=db,
                user_id=user.id,
                event_type="PAYROLL_PROCESSED",
                correlation_key="payroll_record_id",
                correlation_value=record.id,
            )
        ):
            _queue_salary_event_safely(
                db=db,
                background_tasks=background_tasks,
                user_id=user.id,
                event_type="PAYROLL_PROCESSED",
                title="Payroll processed",
                message=(
                    f"Your salary statement for {month_label} "
                    f"{payroll_run.year} is available. This is a "
                    "simulated credit, not a bank transfer."
                ),
                email_subject=(
                    f"HRMS: Payroll processed for "
                    f"{month_label} {payroll_run.year}"
                ),
                template_name="payroll_processed.html",
                context_data={
                    "employee_name": employee_name,
                    "month_name": month_label,
                    "year": payroll_run.year,
                    "net_salary": f"₹{record.net_salary:,.2f}",
                    "salary_slip_url": (
                        f"{base_url}/employee/salary-slips"
                    ),
                    "payroll_record_id": record.id,
                },
                extra_data={
                    "payroll_run_id": payroll_run.id,
                    "payroll_record_id": record.id,
                    "credit_status": record.credit_status,
                },
            )

        # Notify the employee that their salary slip is available.
        # Including salary_slip_id in the email context makes this
        # event idempotent when the Generate endpoint is called again.
        if not _email_event_exists(
            db=db,
            user_id=user.id,
            event_type="SALARY_SLIP_GENERATED",
            correlation_key="salary_slip_id",
            correlation_value=slip.id,
        ):
            _queue_salary_event_safely(
                db=db,
                background_tasks=background_tasks,
                user_id=user.id,
                event_type="SALARY_SLIP_GENERATED",
                title="Salary slip available",
                message=(
                    f"Your salary slip for {month_label} "
                    f"{payroll_run.year} has been generated."
                ),
                email_subject=(
                    f"HRMS: Salary slip available for "
                    f"{month_label} {payroll_run.year}"
                ),
                template_name="salary_slip_generated.html",
                context_data={
                    "employee_name": employee_name,
                    "month_name": month_label,
                    "year": payroll_run.year,
                    "download_url": (
                        f"{base_url}/employee/salary-slips"
                    ),
                    "salary_slip_id": slip.id,
                },
                extra_data={
                    "salary_slip_id": slip.id,
                    "payroll_run_id": payroll_run.id,
                    "payroll_record_id": record.id,
                },
            )

    return [
        serialize_salary_slip(slip)
        for slip in slips
    ]


@router.get(
    "",
    response_model=list[SalarySlipRead],
    dependencies=[
        Depends(require_permissions("SALARY_SLIPS.READ_ALL"))
    ],
)
def read_all_salary_slips(
    db: Session = Depends(get_db),
):
    return [
        serialize_salary_slip(slip)
        for slip in list_salary_slips(db)
    ]


@router.get(
    "/me",
    response_model=list[SalarySlipRead],
)
def read_my_salary_slips(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permissions("SALARY_SLIPS.READ_SELF")
    ),
):
    return [
        serialize_salary_slip(slip)
        for slip in list_my_salary_slips(db, current_user)
    ]


@router.get("/{slip_id}/download")
def download_salary_slip(
    slip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permissions("SALARY_SLIPS.DOWNLOAD")
    ),
):
    slip = get_salary_slip(db, slip_id)

    is_privileged = has_privileged_role(current_user)
    is_owner = (
        slip.payroll_record.employee.user_id == current_user.id
    )

    if not is_privileged and not is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot download another employee's salary slip.",
        )

    file_path = get_salary_slip_file(slip)

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=slip.file_name,
        headers={"Cache-Control": "private, no-store"},
    )
