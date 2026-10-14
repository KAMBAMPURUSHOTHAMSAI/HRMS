
import hashlib

import pytest

from app.core.security import create_access_token
from app.models.employee_document import EmployeeDocument
from app.models.user import User
from app.services import document_service


PNG_CONTENT = b"\x89PNG\r\n\x1a\nHRMS-test-image-content"


@pytest.fixture(autouse=True)
def temporary_document_storage(tmp_path, monkeypatch):
    """Keep uploaded test files outside the application's real storage."""

    storage = tmp_path / "employee_documents"
    monkeypatch.setattr(document_service, "STORAGE_ROOT", storage)
    return storage


def upload_own_document(
    client,
    headers,
    *,
    filename="identity.png",
    content=PNG_CONTENT,
    document_type="ID_PROOF",
    description="Test identity document",
):
    return client.post(
        "/api/v1/documents/me",
        headers=headers,
        files={
            "file": (filename, content, "image/png"),
        },
        data={
            "document_type": document_type,
            "description": description,
        },
    )


def upload_for_employee(
    client,
    headers,
    employee_id,
    *,
    filename="employee-document.png",
    content=PNG_CONTENT,
    document_type="OTHER",
):
    return client.post(
        f"/api/v1/documents/employees/{employee_id}",
        headers=headers,
        files={
            "file": (filename, content, "image/png"),
        },
        data={"document_type": document_type},
    )


def token_for(user):
    token = create_access_token(subject=str(user.id))
    return {"Authorization": f"Bearer {token}"}


def test_my_documents_requires_authentication(client):
    response = client.get("/api/v1/documents/me")
    assert response.status_code == 401


def test_employee_without_profile_cannot_list_documents(
    client,
    employee_headers,
):
    response = client.get(
        "/api/v1/documents/me",
        headers=employee_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Employee profile is not configured for this account."
    )


def test_employee_can_upload_and_list_own_document(
    client,
    employee_user,
    employee_headers,
    make_employee,
):
    employee = make_employee(user=employee_user)

    upload_response = upload_own_document(
        client,
        employee_headers,
    )

    assert upload_response.status_code == 201

    document = upload_response.json()
    assert document["employee_id"] == employee.id
    assert document["original_filename"] == "identity.png"
    assert document["content_type"] == "image/png"
    assert document["file_size"] == len(PNG_CONTENT)
    assert document["document_type"] == "ID_PROOF"
    assert document["description"] == "Test identity document"
    assert document["sha256"] == hashlib.sha256(PNG_CONTENT).hexdigest()

    list_response = client.get(
        "/api/v1/documents/me",
        headers=employee_headers,
    )

    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["id"] == document["id"]


def test_path_traversal_filename_is_sanitized(
    client,
    employee_user,
    employee_headers,
    make_employee,
):
    make_employee(user=employee_user)

    response = upload_own_document(
        client,
        employee_headers,
        filename=r"..\..\identity.png",
    )

    assert response.status_code == 201
    assert response.json()["original_filename"] == "identity.png"


def test_empty_document_is_rejected(
    client,
    employee_user,
    employee_headers,
    make_employee,
):
    make_employee(user=employee_user)

    response = upload_own_document(
        client,
        employee_headers,
        content=b"",
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "The uploaded file is empty."


def test_unsupported_file_extension_is_rejected(
    client,
    employee_user,
    employee_headers,
    make_employee,
):
    make_employee(user=employee_user)

    response = upload_own_document(
        client,
        employee_headers,
        filename="notes.txt",
        content=b"some text",
    )

    assert response.status_code == 422
    assert "Unsupported file type" in response.json()["detail"]


def test_file_signature_must_match_extension(
    client,
    employee_user,
    employee_headers,
    make_employee,
):
    make_employee(user=employee_user)

    response = upload_own_document(
        client,
        employee_headers,
        filename="incorrect.png",
        content=b"%PDF-1.7 document content",
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "The file content does not match its filename extension."
    )


def test_invalid_document_category_is_rejected(
    client,
    employee_user,
    employee_headers,
    make_employee,
):
    make_employee(user=employee_user)

    response = upload_own_document(
        client,
        employee_headers,
        document_type="INVALID_CATEGORY",
    )

    assert response.status_code == 422
    assert "Invalid document type" in response.json()["detail"]


def test_document_over_five_mb_is_rejected(
    client,
    employee_user,
    employee_headers,
    make_employee,
):
    make_employee(user=employee_user)

    content = b"\x89PNG\r\n\x1a\n" + (
        b"x" * (5 * 1024 * 1024)
    )

    response = upload_own_document(
        client,
        employee_headers,
        content=content,
    )

    assert response.status_code == 413
    assert response.json()["detail"] == "File size cannot exceed 5 MB."


def test_employee_can_download_own_document(
    client,
    employee_user,
    employee_headers,
    make_employee,
):
    make_employee(user=employee_user)

    upload_response = upload_own_document(
        client,
        employee_headers,
    )
    assert upload_response.status_code == 201

    document_id = upload_response.json()["id"]

    response = client.get(
        f"/api/v1/documents/{document_id}/download",
        headers=employee_headers,
    )

    assert response.status_code == 200
    assert response.content == PNG_CONTENT
    assert response.headers["content-type"].startswith("image/png")
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_employee_cannot_download_another_employees_document(
    client,
    db,
    employee_user,
    employee_headers,
    make_employee,
    make_user,
):
    owner = make_employee(user=employee_user)

    owner_upload = upload_own_document(
        client,
        employee_headers,
    )
    assert owner_upload.status_code == 201

    other_user = make_user(
        email="other.document.employee@example.com",
        role_name="EMPLOYEE",
    )
    make_employee(user=other_user)

    response = client.get(
        f"/api/v1/documents/{owner_upload.json()['id']}/download",
        headers=token_for(other_user),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "You cannot download another employee's document."
    )


def test_admin_can_list_and_download_employee_documents(
    client,
    admin_headers,
    employee_user,
    employee_headers,
    make_employee,
):
    make_employee(user=employee_user)

    upload_response = upload_own_document(
        client,
        employee_headers,
    )
    assert upload_response.status_code == 201

    document_id = upload_response.json()["id"]

    list_response = client.get(
        "/api/v1/documents",
        headers=admin_headers,
    )

    assert list_response.status_code == 200
    assert any(
        document["id"] == document_id
        for document in list_response.json()
    )

    download_response = client.get(
        f"/api/v1/documents/{document_id}/download",
        headers=admin_headers,
    )

    assert download_response.status_code == 200
    assert download_response.content == PNG_CONTENT


def test_hr_can_upload_document_for_an_employee(
    client,
    hr_headers,
    employee_user,
    make_employee,
):
    employee = make_employee(user=employee_user)

    response = upload_for_employee(
        client,
        hr_headers,
        employee.id,
        document_type="CONTRACT",
    )

    assert response.status_code == 201
    assert response.json()["employee_id"] == employee.id
    assert response.json()["document_type"] == "CONTRACT"


def test_employee_cannot_list_all_employee_documents(
    client,
    employee_headers,
):
    response = client.get(
        "/api/v1/documents",
        headers=employee_headers,
    )

    assert response.status_code == 403


def test_upload_for_missing_employee_returns_not_found(
    client,
    admin_headers,
):
    response = upload_for_employee(
        client,
        admin_headers,
        99999,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Employee not found."


def test_missing_document_download_returns_not_found(
    client,
    admin_headers,
):
    response = client.get(
        "/api/v1/documents/99999/download",
        headers=admin_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Employee document not found."


def test_employee_can_delete_own_document(
    client,
    db,
    employee_user,
    employee_headers,
    make_employee,
):
    make_employee(user=employee_user)

    upload_response = upload_own_document(
        client,
        employee_headers,
    )
    assert upload_response.status_code == 201

    document_id = upload_response.json()["id"]

    response = client.delete(
        f"/api/v1/documents/{document_id}",
        headers=employee_headers,
    )

    assert response.status_code == 200
    assert response.json()["message"] == (
        "Employee document deleted successfully."
    )

    assert db.get(EmployeeDocument, document_id) is None


def test_employee_cannot_delete_another_employees_document(
    client,
    employee_user,
    employee_headers,
    make_employee,
    make_user,
):
    make_employee(user=employee_user)

    upload_response = upload_own_document(
        client,
        employee_headers,
    )
    assert upload_response.status_code == 201

    other_user = make_user(
        email="delete.other.document@example.com",
        role_name="EMPLOYEE",
    )
    make_employee(user=other_user)

    response = client.delete(
        f"/api/v1/documents/{upload_response.json()['id']}",
        headers=token_for(other_user),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "You cannot delete another employee's document."
    )


def test_admin_can_delete_an_employee_document(
    client,
    db,
    admin_headers,
    employee_user,
    employee_headers,
    make_employee,
):
    make_employee(user=employee_user)

    upload_response = upload_own_document(
        client,
        employee_headers,
    )
    assert upload_response.status_code == 201

    document_id = upload_response.json()["id"]

    response = client.delete(
        f"/api/v1/documents/{document_id}",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert db.get(EmployeeDocument, document_id) is None
