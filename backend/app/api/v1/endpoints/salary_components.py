
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.permissions import require_permissions
from app.models.user import User
from app.schemas.salary_component import (
    SalaryComponentCreate,
    SalaryComponentRead,
    SalaryComponentUpdate,
)
from app.services.salary_component_service import (
    create_salary_component,
    deactivate_salary_component,
    list_salary_components,
    update_salary_component,
)


router = APIRouter(
    prefix="/salary-components",
    tags=["Salary Components"],
)


@router.get(
    "",
    response_model=list[SalaryComponentRead],
)
def read_salary_components(
    include_inactive: bool = True,
    db: Session = Depends(get_db),
    _current_user: User = Depends(
        require_permissions("PAYROLL.COMPONENTS_READ")
    ),
):
    return list_salary_components(
        db,
        include_inactive=include_inactive,
    )


@router.post(
    "",
    response_model=SalaryComponentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_component(
    payload: SalaryComponentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permissions("PAYROLL.COMPONENTS_MANAGE")
    ),
):
    return create_salary_component(
        db,
        payload,
        current_user.id,
    )


@router.patch(
    "/{component_id}",
    response_model=SalaryComponentRead,
)
def update_component(
    component_id: int,
    payload: SalaryComponentUpdate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(
        require_permissions("PAYROLL.COMPONENTS_MANAGE")
    ),
):
    return update_salary_component(
        db,
        component_id,
        payload,
    )


@router.delete(
    "/{component_id}",
    response_model=SalaryComponentRead,
)
def deactivate_component(
    component_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(
        require_permissions("PAYROLL.COMPONENTS_MANAGE")
    ),
):
    return deactivate_salary_component(
        db,
        component_id,
    )
