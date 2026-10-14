
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import settings
from app.core.permissions import require_permissions
from app.models.user import User
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeRead,
    EmployeeSelfUpdate,
    EmployeeUpdate,
)
from app.services.employee_service import (
    create_employee,
    deactivate_employee,
    get_employee_or_404,
    list_employees,
    serialize_employee,
    update_employee,
    update_my_employee_profile,
)
from app.services.notification_service import publish_user_event


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/employees",
    tags=["Employees"],
)


@router.get("/me", response_model=EmployeeRead)
def read_my_employee_profile(
    current_user: User = Depends(
        require_permissions("EMPLOYEES.READ_SELF")
    ),
):
    if current_user.employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile is not configured for this account",
        )

    return serialize_employee(current_user.employee)


@router.patch("/me", response_model=EmployeeRead)
def edit_my_employee_profile(
    payload: EmployeeSelfUpdate,
    current_user: User = Depends(
        require_permissions("EMPLOYEES.UPDATE_SELF")
    ),
    db: Session = Depends(get_db),
):
    if current_user.employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile is not configured for this account",
        )

    return update_my_employee_profile(
        db,
        current_user.employee.id,
        payload,
    )


@router.get(
    "",
    response_model=list[EmployeeRead],
    dependencies=[
        Depends(require_permissions("EMPLOYEES.READ"))
    ],
)
def read_employees(db: Session = Depends(get_db)):
    return list_employees(db)


@router.post(
    "",
    response_model=EmployeeRead,
    status_code=status.HTTP_201_CREATED,
)
def add_employee(
    payload: EmployeeCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _actor: User = Depends(
        require_permissions("EMPLOYEES.CREATE")
    ),
):
    employee = create_employee(db, payload)

    # Employee creation has already committed successfully.
    # Email failure must not make the client retry creation.
    try:
        publish_user_event(
            db=db,
            background_tasks=background_tasks,
            user_id=employee.user_id,
            event_type="EMPLOYEE_ONBOARDED",
            title="Welcome to HRMS",
            message=(
                f"Your HRMS account is ready. "
                f"Employee Code: {employee.employee_code}"
            ),
            email_subject="Welcome to HRMS",
            template_name="employee_onboarding.html",
            context_data={
                "first_name": employee.first_name,
                "employee_code": employee.employee_code,
                "login_url": (
                    f"{settings.frontend_base_url.rstrip('/')}/login"
                ),
            },
            extra_data={
                "employee_id": employee.id,
                "employee_code": employee.employee_code,
            },
        )
    except Exception:
        logger.exception(
            "Employee %s was created, but the welcome email "
            "could not be queued.",
            employee.id,
        )

    return employee


@router.get(
    "/{employee_id}",
    response_model=EmployeeRead,
    dependencies=[
        Depends(require_permissions("EMPLOYEES.READ"))
    ],
)
def read_employee(
    employee_id: int,
    db: Session = Depends(get_db),
):
    return serialize_employee(
        get_employee_or_404(db, employee_id)
    )


@router.patch(
    "/{employee_id}",
    response_model=EmployeeRead,
    dependencies=[
        Depends(require_permissions("EMPLOYEES.UPDATE"))
    ],
)
def edit_employee(
    employee_id: int,
    payload: EmployeeUpdate,
    db: Session = Depends(get_db),
):
    return update_employee(db, employee_id, payload)


@router.delete(
    "/{employee_id}",
    response_model=EmployeeRead,
    dependencies=[
        Depends(require_permissions("EMPLOYEES.DELETE"))
    ],
)
def remove_employee(
    employee_id: int,
    db: Session = Depends(get_db),
):
    return deactivate_employee(db, employee_id)
