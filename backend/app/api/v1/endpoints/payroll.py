
import logging
from calendar import month_name

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.core.permissions import require_permissions
from app.models.employee import Employee
from app.models.payroll_record import PayrollRecord
from app.models.user import User
from app.schemas.payroll import (
    PayrollAdjustmentCreate,
    PayrollAdjustmentRead,
    PayrollGenerateRequest,
    PayrollRecordRead,
    PayrollRunRead,
)
from app.services.notification_service import publish_user_event
from app.services.payroll_service import (
    add_payroll_adjustment,
    generate_payroll_run,
    get_payroll_run,
    list_my_payroll_records,
    list_payroll_runs,
    list_run_records,
    lock_payroll,
    serialize_adjustment,
    serialize_payroll_record,
    serialize_payroll_run,
    simulate_salary_credit,
)


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/payroll",
    tags=["Payroll"],
)


def _queue_payroll_event_safely(
    db: Session,
    background_tasks: BackgroundTasks,
    **event_data,
) -> None:
    """
    Queue a payroll notification and email without undoing
    a completed payroll operation if notification queuing fails.
    """
    try:
        publish_user_event(
            db=db,
            background_tasks=background_tasks,
            **event_data,
        )
    except Exception:
        logger.exception(
            "Could not queue payroll notification: %s",
            event_data.get("event_type"),
        )


@router.post(
    "/runs/generate",
    response_model=PayrollRunRead,
    status_code=status.HTTP_201_CREATED,
)
def generate_run(
    payload: PayrollGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permissions("PAYROLL.GENERATE")
    ),
):
    run = generate_payroll_run(
        db,
        payload.year,
        payload.month,
        current_user,
    )
    return serialize_payroll_run(run)


@router.get(
    "/runs",
    response_model=list[PayrollRunRead],
    dependencies=[
        Depends(require_permissions("PAYROLL.READ_RUNS"))
    ],
)
def read_payroll_runs(
    db: Session = Depends(get_db),
):
    return [
        serialize_payroll_run(run)
        for run in list_payroll_runs(db)
    ]


@router.get(
    "/runs/{run_id}",
    response_model=PayrollRunRead,
    dependencies=[
        Depends(require_permissions("PAYROLL.READ_RUNS"))
    ],
)
def read_payroll_run(
    run_id: int,
    db: Session = Depends(get_db),
):
    run = get_payroll_run(db, run_id)
    return serialize_payroll_run(run)


@router.get(
    "/runs/{run_id}/records",
    response_model=list[PayrollRecordRead],
    dependencies=[
        Depends(require_permissions("PAYROLL.READ_RECORDS"))
    ],
)
def read_payroll_records(
    run_id: int,
    db: Session = Depends(get_db),
):
    return [
        serialize_payroll_record(record)
        for record in list_run_records(db, run_id)
    ]


@router.post(
    "/runs/{run_id}/adjustments",
    response_model=PayrollAdjustmentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_adjustment(
    run_id: int,
    payload: PayrollAdjustmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permissions("PAYROLL.ADJUST")
    ),
):
    adjustment = add_payroll_adjustment(
        db,
        run_id,
        payload,
        current_user,
    )
    return serialize_adjustment(adjustment)


@router.post(
    "/runs/{run_id}/lock",
    response_model=PayrollRunRead,
)
def finalize_payroll(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permissions("PAYROLL.FINALIZE")
    ),
):
    run = lock_payroll(db, run_id, current_user)
    return serialize_payroll_run(run)


@router.post(
    "/runs/{run_id}/simulate-credit",
    response_model=PayrollRunRead,
)
def simulate_credit(
    run_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _current_user: User = Depends(
        require_permissions("PAYROLL.SIMULATE_CREDIT")
    ),
):
    # Simulate the salary credit first.
    # The service validates the payroll run and commits the
    # simulated credit status before notifications are queued.
    run = simulate_salary_credit(db, run_id)

    # Load payroll records together with their employee accounts.
    records = db.scalars(
        select(PayrollRecord)
        .where(PayrollRecord.payroll_run_id == run_id)
        .options(
            selectinload(PayrollRecord.employee).selectinload(
                Employee.user
            )
        )
        .order_by(PayrollRecord.employee_id)
    ).all()

    base_url = getattr(
        settings,
        "frontend_base_url",
        "http://localhost:5174",
    ).rstrip("/")

    month_label = month_name[run.month]

    # Notify each active employee included in this payroll run.
    for record in records:
        employee = record.employee
        user = employee.user if employee else None

        if user is None or not user.is_active:
            continue

        employee_name = " ".join(
            part
            for part in (user.first_name, user.last_name)
            if part
        )

        _queue_payroll_event_safely(
            db=db,
            background_tasks=background_tasks,
            user_id=user.id,
            event_type="PAYROLL_PROCESSED",
            title="Payroll processed",
            message=(
                f"Your salary statement for {month_label} "
                f"{run.year} is available. This is a simulated "
                "credit, not a bank transfer."
            ),
            email_subject=(
                f"HRMS: Payroll processed for "
                f"{month_label} {run.year}"
            ),
            template_name="payroll_processed.html",
            context_data={
                "employee_name": employee_name,
                "month_name": month_label,
                "year": run.year,
                "net_salary": f"₹{record.net_salary:,.2f}",
                "salary_slip_url": (
                    f"{base_url}/employee/salary-slips"
                ),
            },
            extra_data={
                "payroll_run_id": run.id,
                "payroll_record_id": record.id,
                "credit_status": record.credit_status,
            },
        )

    return serialize_payroll_run(run)


@router.get(
    "/me",
    response_model=list[PayrollRecordRead],
)
def read_my_payroll(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permissions("PAYROLL.READ_SELF")
    ),
):
    return [
        serialize_payroll_record(record)
        for record in list_my_payroll_records(db, current_user)
    ]
