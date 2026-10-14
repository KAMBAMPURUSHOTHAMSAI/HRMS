
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EmployeeDocumentRead(BaseModel):
    id: int
    employee_id: int
    uploaded_by_user_id: int | None

    original_filename: str
    content_type: str
    file_size: int

    document_type: str
    description: str | None
    sha256: str

    created_at: datetime

    employee_code: str | None = None
    employee_name: str | None = None
    employee_email: str | None = None

    model_config = ConfigDict(from_attributes=True)


class EmployeeDocumentMetadataUpdate(BaseModel):
    document_type: str | None = Field(default=None, max_length=50)
    description: str | None = Field(default=None, max_length=1000)

    model_config = ConfigDict(extra="forbid")
