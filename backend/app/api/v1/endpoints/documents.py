
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.permissions import require_permissions
from app.models.employee import Employee
from app.models.user import User
from app.schemas.document import EmployeeDocumentRead
from app.services.document_service import (
    delete_employee_document,
    get_document_or_404,
    list_employee_documents,
    resolve_document_file,
    save_employee_document,
    serialize_document,
)
from app.utils.file_validation import MAX_DOCUMENT_SIZE_BYTES


router = APIRouter(
    prefix="/documents",
    tags=["Employee Documents"],
)


def has_privileged_role(user: User) -> bool:
    return any(
        assignment.role is not None
        and assignment.role.is_active
        and assignment.role.name in {"ADMIN", "HR"}
        for assignment in user.user_roles
    )


def get_my_employee_or_404(current_user: User) -> Employee:
    employee = current_user.employee

    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile is not configured for this account.",
        )

    return employee


def upload_document(
    db: Session,
    employee: Employee,
    current_user: User,
    file: UploadFile,
    document_type: str,
    description: str | None,
):
    contents = file.file.read(MAX_DOCUMENT_SIZE_BYTES + 1)

    if len(contents) > MAX_DOCUMENT_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size cannot exceed 5 MB.",
        )

    try:
        document = save_employee_document(
            db=db,
            employee=employee,
            uploader=current_user,
            filename=file.filename,
            content=contents,
            document_type=document_type,
            description=description,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return serialize_document(document)


@router.get(
    "/me",
    response_model=list[EmployeeDocumentRead],
)
def read_my_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permissions("DOCUMENTS.READ_SELF")
    ),
):
    employee = get_my_employee_or_404(current_user)

    documents = list_employee_documents(
        db,
        employee_id=employee.id,
    )

    return [
        serialize_document(document)
        for document in documents
    ]


@router.post(
    "/me",
    response_model=EmployeeDocumentRead,
    status_code=status.HTTP_201_CREATED,
)
def upload_my_document(
    file: UploadFile = File(...),
    document_type: str = Form(default="OTHER"),
    description: str | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permissions("DOCUMENTS.UPLOAD_SELF")
    ),
):
    employee = get_my_employee_or_404(current_user)

    return upload_document(
        db,
        employee,
        current_user,
        file,
        document_type,
        description,
    )


@router.get(
    "",
    response_model=list[EmployeeDocumentRead],
    dependencies=[
        Depends(require_permissions("DOCUMENTS.READ_ALL"))
    ],
)
def read_all_documents(
    employee_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
):
    documents = list_employee_documents(
        db,
        employee_id=employee_id,
    )

    return [
        serialize_document(document)
        for document in documents
    ]


@router.post(
    "/employees/{employee_id}",
    response_model=EmployeeDocumentRead,
    status_code=status.HTTP_201_CREATED,
)
def upload_for_employee(
    employee_id: int,
    file: UploadFile = File(...),
    document_type: str = Form(default="OTHER"),
    description: str | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permissions("DOCUMENTS.UPLOAD_FOR_EMPLOYEE")
    ),
):
    employee = db.get(Employee, employee_id)

    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found.",
        )

    return upload_document(
        db,
        employee,
        current_user,
        file,
        document_type,
        description,
    )


@router.get("/{document_id}/download")
def download_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permissions("DOCUMENTS.DOWNLOAD")
    ),
):
    document = get_document_or_404(db, document_id)

    is_owner = (
        document.employee is not None
        and document.employee.user_id == current_user.id
    )

    if not is_owner and not has_privileged_role(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot download another employee's document.",
        )

    file_path = resolve_document_file(document)

    return FileResponse(
        path=file_path,
        media_type=document.content_type,
        filename=document.original_filename,
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_200_OK,
)
def remove_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permissions("DOCUMENTS.DELETE")
    ),
):
    document = get_document_or_404(db, document_id)

    is_owner = (
        document.employee is not None
        and document.employee.user_id == current_user.id
    )

    if not is_owner and not has_privileged_role(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot delete another employee's document.",
        )

    delete_employee_document(db, document)

    return {
        "message": "Employee document deleted successfully."
    }
