
from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.permissions import require_permissions
from app.models.user import User
from app.schemas.employee_salary_component import (
    EmployeeSalaryComponentCreate,
    EmployeeSalaryComponentRead,
    EmployeeSalaryComponentUpdate,
)
from app.services.employee_salary_component_service import (
    create_employee_salary_component,
    list_employee_salary_components,
    update_employee_salary_component,
)


router = APIRouter(
    prefix="/employee-salary-components",
    tags=["Employee Salary Components"],
)


@router.get(
    "",
    response_model=list[EmployeeSalaryComponentRead],
)
def read_employee_salary_components(
    employee_id: int | None = Query(default=None, gt=0),
    as_of_date: date | None = None,
    db: Session = Depends(get_db),
    _current_user: User = Depends(
        require_permissions("PAYROLL.COMPONENTS_READ")
    ),
):
    return list_employee_salary_components(
        db=db,
        employee_id=employee_id,
        as_of_date=as_of_date,
    )


@router.post(
    "",
    response_model=EmployeeSalaryComponentRead,
    status_code=status.HTTP_201_CREATED,
)
def assign_employee_salary_component(
    payload: EmployeeSalaryComponentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permissions("PAYROLL.COMPONENTS_MANAGE")
    ),
):
    return create_employee_salary_component(
        db=db,
        payload=payload,
        actor_user_id=current_user.id,
    )


@router.patch(
    "/{assignment_id}",
    response_model=EmployeeSalaryComponentRead,
)
def update_employee_salary_component_assignment(
    assignment_id: int,
    payload: EmployeeSalaryComponentUpdate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(
        require_permissions("PAYROLL.COMPONENTS_MANAGE")
    ),
):
    return update_employee_salary_component(
        db=db,
        assignment_id=assignment_id,
        payload=payload,
    )
