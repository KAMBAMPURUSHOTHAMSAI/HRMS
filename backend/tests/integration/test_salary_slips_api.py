from datetime import date

import pytest

import app.api.v1.endpoints.salary_slips as salary_slips_endpoint

from app.services import payroll_service, salary_slip_service


PAYROLL_YEAR = 2026
PAYROLL_MONTH = 9


@pytest.fixture(autouse=True)
def isolate_salary_slip_storage(tmp_path, monkeypatch):
    """Generate PDFs only in a temporary test directory."""

    monkeypatch.setattr(
        salary_slip_service,
        "STORAGE_ROOT",
        tmp_path / "salary_slips",
    )
    monkeypatch.setattr(
        payroll_service,
        "company_today",
        lambda: date(2026, 10, 13),
    )

    # Notifications and email are tested separately.
    monkeypatch.setattr(
        salary_slips_endpoint,
        "_queue_salary_event_safely",
        lambda **kwargs: None,
    )


def create_locked_payroll_run(client, admin_headers):
    """Create and lock September 2026 payroll."""

    generated = client.post(
        "/api/v1/payroll/runs/generate",
        headers=admin_headers,
        json={
            "year": PAYROLL_YEAR,
            "month": PAYROLL_MONTH,
        },
    )

    assert generated.status_code == 201, generated.text

    run_id = generated.json()["id"]

    locked = client.post(
        f"/api/v1/payroll/runs/{run_id}/lock",
        headers=admin_headers,
    )

    assert locked.status_code == 200, locked.text
    assert locked.json()["status"] == "LOCKED"

    return run_id


def generate_slips(client, admin_headers, run_id):
    return client.post(
        f"/api/v1/salary-slips/payroll-runs/{run_id}/generate",
        headers=admin_headers,
    )


def test_salary_slip_generation_requires_authentication(client):
    response = client.post(
        "/api/v1/salary-slips/payroll-runs/1/generate",
    )

    assert response.status_code == 401


def test_employee_cannot_generate_salary_slips(
    client,
    employee_headers,
):
    response = client.post(
        "/api/v1/salary-slips/payroll-runs/1/generate",
        headers=employee_headers,
    )

    assert response.status_code == 403


def test_salary_slips_require_locked_payroll(
    client,
    admin_headers,
    make_employee,
):
    make_employee()

    generated = client.post(
        "/api/v1/payroll/runs/generate",
        headers=admin_headers,
        json={
            "year": PAYROLL_YEAR,
            "month": PAYROLL_MONTH,
        },
    )

    assert generated.status_code == 201
    run_id = generated.json()["id"]

    response = generate_slips(
        client,
        admin_headers,
        run_id,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Lock payroll before generating salary slips"
    )


def test_admin_can_generate_salary_slip_pdf(
    client,
    admin_headers,
    employee_user,
    make_employee,
):
    make_employee(user=employee_user)

    run_id = create_locked_payroll_run(
        client,
        admin_headers,
    )

    response = generate_slips(
        client,
        admin_headers,
        run_id,
    )

    assert response.status_code == 201, response.text

    slips = response.json()
    assert len(slips) == 1

    slip = slips[0]
    assert slip["employee_email"] == employee_user.email
    assert slip["year"] == PAYROLL_YEAR
    assert slip["month"] == PAYROLL_MONTH
    assert slip["file_name"].lower().endswith(".pdf")
    assert slip["net_salary"] == "0.00"


def test_generating_slips_again_reuses_the_existing_slip(
    client,
    admin_headers,
    make_employee,
):
    make_employee()

    run_id = create_locked_payroll_run(
        client,
        admin_headers,
    )

    first = generate_slips(client, admin_headers, run_id)
    assert first.status_code == 201

    second = generate_slips(client, admin_headers, run_id)
    assert second.status_code == 201

    assert len(first.json()) == 1
    assert len(second.json()) == 1
    assert second.json()[0]["id"] == first.json()[0]["id"]


def test_admin_can_list_salary_slips(
    client,
    admin_headers,
    make_employee,
):
    make_employee()

    run_id = create_locked_payroll_run(
        client,
        admin_headers,
    )
    generated = generate_slips(client, admin_headers, run_id)
    assert generated.status_code == 201

    response = client.get(
        "/api/v1/salary-slips",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_employee_cannot_list_all_salary_slips(
    client,
    employee_headers,
):
    response = client.get(
        "/api/v1/salary-slips",
        headers=employee_headers,
    )

    assert response.status_code == 403


def test_employee_can_list_own_salary_slips(
    client,
    admin_headers,
    employee_user,
    employee_headers,
    make_employee,
):
    make_employee(user=employee_user)

    run_id = create_locked_payroll_run(
        client,
        admin_headers,
    )

    generated = generate_slips(
        client,
        admin_headers,
        run_id,
    )
    assert generated.status_code == 201

    response = client.get(
        "/api/v1/salary-slips/me",
        headers=employee_headers,
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["employee_email"] == employee_user.email


def test_salary_slip_download_returns_pdf(
    client,
    admin_headers,
    employee_user,
    employee_headers,
    make_employee,
):
    make_employee(user=employee_user)

    run_id = create_locked_payroll_run(
        client,
        admin_headers,
    )

    generated = generate_slips(
        client,
        admin_headers,
        run_id,
    )
    assert generated.status_code == 201

    slip_id = generated.json()[0]["id"]

    response = client.get(
        f"/api/v1/salary-slips/{slip_id}/download",
        headers=employee_headers,
    )

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF-")
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["cache-control"] == "private, no-store"


def test_employee_cannot_download_another_employees_slip(
    client,
    admin_headers,
    employee_user,
    employee_headers,
    make_employee,
    make_user,
):
    first_employee = make_employee(user=employee_user)

    other_user = make_user(
        email="other.salary.slip@example.com",
        role_name="EMPLOYEE",
    )
    other_employee = make_employee(user=other_user)

    run_id = create_locked_payroll_run(
        client,
        admin_headers,
    )

    generated = generate_slips(
        client,
        admin_headers,
        run_id,
    )
    assert generated.status_code == 201

    other_slip = next(
        item
        for item in generated.json()
        if item["employee_id"] == other_employee.id
    )

    assert other_employee.id != first_employee.id

    response = client.get(
        f"/api/v1/salary-slips/{other_slip['id']}/download",
        headers=employee_headers,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "You cannot download another employee's salary slip."
    )


def test_missing_salary_slip_returns_not_found(
    client,
    admin_headers,
):
    response = client.get(
        "/api/v1/salary-slips/99999/download",
        headers=admin_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Salary slip not found"


def test_employee_without_profile_gets_not_found(
    client,
    employee_headers,
):
    response = client.get(
        "/api/v1/salary-slips/me",
        headers=employee_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Employee profile is not configured for this account"
    )