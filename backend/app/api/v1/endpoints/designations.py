
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.permissions import require_permissions
from app.schemas.designation import (
    DesignationCreate,
    DesignationRead,
    DesignationUpdate,
)
from app.services.designation_service import (
    create_designation,
    deactivate_designation,
    get_designation,
    list_designations,
    update_designation,
)


router = APIRouter(
    prefix="/designations",
    tags=["Designations"],
)


@router.get(
    "",
    response_model=list[DesignationRead],
    dependencies=[
        Depends(require_permissions("DESIGNATIONS.READ"))
    ],
)
def read_designations(db: Session = Depends(get_db)):
    return list_designations(db)


@router.post(
    "",
    response_model=DesignationRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(require_permissions("DESIGNATIONS.CREATE"))
    ],
)
def add_designation(
    payload: DesignationCreate,
    db: Session = Depends(get_db),
):
    return create_designation(db, payload)


@router.get(
    "/{designation_id}",
    response_model=DesignationRead,
    dependencies=[
        Depends(require_permissions("DESIGNATIONS.READ"))
    ],
)
def read_designation(
    designation_id: int,
    db: Session = Depends(get_db),
):
    return get_designation(db, designation_id)


@router.patch(
    "/{designation_id}",
    response_model=DesignationRead,
    dependencies=[
        Depends(require_permissions("DESIGNATIONS.UPDATE"))
    ],
)
def edit_designation(
    designation_id: int,
    payload: DesignationUpdate,
    db: Session = Depends(get_db),
):
    return update_designation(db, designation_id, payload)


@router.delete(
    "/{designation_id}",
    response_model=DesignationRead,
    dependencies=[
        Depends(require_permissions("DESIGNATIONS.DELETE"))
    ],
)
def remove_designation(
    designation_id: int,
    db: Session = Depends(get_db),
):
    return deactivate_designation(db, designation_id)
