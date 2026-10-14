
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.permissions import require_permissions
from app.schemas.department import (
    DepartmentCreate,
    DepartmentRead,
    DepartmentUpdate,
)
from app.services.department_service import (
    create_department,
    deactivate_department,
    get_department,
    list_departments,
    update_department,
)


router = APIRouter(
    prefix="/departments",
    tags=["Departments"],
)


@router.get(
    "",
    response_model=list[DepartmentRead],
    dependencies=[
        Depends(require_permissions("DEPARTMENTS.READ"))
    ],
)
def read_departments(db: Session = Depends(get_db)):
    return list_departments(db)


@router.post(
    "",
    response_model=DepartmentRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(require_permissions("DEPARTMENTS.CREATE"))
    ],
)
def add_department(
    payload: DepartmentCreate,
    db: Session = Depends(get_db),
):
    return create_department(db, payload)


@router.get(
    "/{department_id}",
    response_model=DepartmentRead,
    dependencies=[
        Depends(require_permissions("DEPARTMENTS.READ"))
    ],
)
def read_department(
    department_id: int,
    db: Session = Depends(get_db),
):
    return get_department(db, department_id)


@router.patch(
    "/{department_id}",
    response_model=DepartmentRead,
    dependencies=[
        Depends(require_permissions("DEPARTMENTS.UPDATE"))
    ],
)
def edit_department(
    department_id: int,
    payload: DepartmentUpdate,
    db: Session = Depends(get_db),
):
    return update_department(db, department_id, payload)


@router.delete(
    "/{department_id}",
    response_model=DepartmentRead,
    dependencies=[
        Depends(require_permissions("DEPARTMENTS.DELETE"))
    ],
)
def remove_department(
    department_id: int,
    db: Session = Depends(get_db),
):
    return deactivate_department(db, department_id)
