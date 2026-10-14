
import hashlib
import logging
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.employee import Employee
from app.models.employee_document import EmployeeDocument
from app.models.user import User
from app.utils.file_validation import (
    DOCUMENT_TYPES,
    validate_document_upload,
)


logger = logging.getLogger(__name__)

STORAGE_ROOT = (
    Path(__file__).resolve().parents[2]
    / "storage"
    / "employee_documents"
)


def _document_query(db: Session):
    return db.query(EmployeeDocument).options(
        joinedload(EmployeeDocument.employee).joinedload(
            Employee.user
        )
    )


def get_document_or_404(
    db: Session,
    document_id: int,
) -> EmployeeDocument:
    document = (
        _document_query(db)
        .filter(EmployeeDocument.id == document_id)
        .first()
    )

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee document not found.",
        )

    return document


def list_employee_documents(
    db: Session,
    employee_id: int | None = None,
) -> list[EmployeeDocument]:
    query = _document_query(db)

    if employee_id is not None:
        query = query.filter(
            EmployeeDocument.employee_id == employee_id
        )

    return query.order_by(
        EmployeeDocument.created_at.desc(),
        EmployeeDocument.id.desc(),
    ).all()


def serialize_document(document: EmployeeDocument) -> dict:
    employee = document.employee

    employee_name = None
    employee_email = None
    employee_code = None

    if employee is not None:
        employee_code = employee.employee_code

        if employee.user is not None:
            employee_name = (
                f"{employee.user.first_name} "
                f"{employee.user.last_name}"
            ).strip()
            employee_email = employee.user.email

    return {
        "id": document.id,
        "employee_id": document.employee_id,
        "uploaded_by_user_id": document.uploaded_by_user_id,
        "original_filename": document.original_filename,
        "content_type": document.content_type,
        "file_size": document.file_size,
        "document_type": document.document_type,
        "description": document.description,
        "sha256": document.sha256,
        "created_at": document.created_at,
        "employee_code": employee_code,
        "employee_name": employee_name,
        "employee_email": employee_email,
    }


def save_employee_document(
    db: Session,
    employee: Employee,
    uploader: User,
    filename: str | None,
    content: bytes,
    document_type: str,
    description: str | None,
) -> EmployeeDocument:
    safe_name, content_type, extension = validate_document_upload(
        filename,
        content,
    )

    category = (document_type or "OTHER").strip().upper()

    if category not in DOCUMENT_TYPES:
        raise ValueError(
            "Invalid document type. Choose ID_PROOF, CONTRACT, "
            "CERTIFICATE, RESUME, or OTHER."
        )

    clean_description = (
        description.strip() if description is not None else None
    )

    if clean_description == "":
        clean_description = None

    if clean_description and len(clean_description) > 1000:
        raise ValueError("Description cannot exceed 1000 characters.")

    # Never use the user-provided filename as the storage filename.
    relative_path = (
        Path(str(employee.id))
        / f"{uuid4().hex}{extension}"
    )

    STORAGE_ROOT.mkdir(parents=True, exist_ok=True)

    target_path = (STORAGE_ROOT / relative_path).resolve()
    root_path = STORAGE_ROOT.resolve()

    if not target_path.is_relative_to(root_path):
        raise ValueError("Invalid storage path.")

    target_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        target_path.write_bytes(content)

        document = EmployeeDocument(
            employee_id=employee.id,
            uploaded_by_user_id=uploader.id,
            original_filename=safe_name,
            storage_path=relative_path.as_posix(),
            content_type=content_type,
            file_size=len(content),
            document_type=category,
            description=clean_description,
            sha256=hashlib.sha256(content).hexdigest(),
        )

        db.add(document)
        db.commit()
        db.refresh(document)

        document_id = document.id

    except Exception:
        db.rollback()

        try:
            target_path.unlink(missing_ok=True)
        except OSError:
            logger.exception("Failed to clean up an uploaded document.")

        raise

    return get_document_or_404(db, document_id)


def resolve_document_file(
    document: EmployeeDocument,
    require_exists: bool = True,
) -> Path:
    root_path = STORAGE_ROOT.resolve()
    file_path = (root_path / document.storage_path).resolve()

    if not file_path.is_relative_to(root_path):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invalid stored document path.",
        )

    if require_exists and not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The stored document file is missing.",
        )

    return file_path


def delete_employee_document(
    db: Session,
    document: EmployeeDocument,
) -> None:
    file_path = resolve_document_file(
        document,
        require_exists=False,
    )

    try:
        db.delete(document)
        db.commit()
    except Exception:
        db.rollback()
        raise

    try:
        file_path.unlink(missing_ok=True)
    except OSError:
        # The metadata has already been removed. Keep this failure
        # visible in server logs so orphaned storage files can be cleaned up.
        logger.exception(
            "Failed to remove deleted document file %s",
            document.id,
        )
