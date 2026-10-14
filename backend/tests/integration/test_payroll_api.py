from datetime import date

import app.api.v1.endpoints.payroll as payroll_endpoint
from app.services import payroll_service

import pytest


PAYROLL_YEAR = 2026
PAYROLL_MONTH = 9


@pytest.fixture(autouse=True)
def freeze_payroll_clock(monkeypatch):
    """Use a fixed date so September 2026 is a completed period."""

    monkeypatch.setattr(
        payroll_service,
        "company_today",
        lambda: date(2026, 10, 13),
    )


def generate_payroll(client, headers):
    return client.post(
        "/api/v1/payroll/runs/generate",
        headers=headers,
        json={
            "year": PAYROLL_YEAR,
            "month": PAYROLL_MONTH,
        },
    )


def test_generate_payroll_requires_authentication(client):
    response = client.post(
        "/api/v1/payroll/runs/generate",
        json={
            "year": PAYROLL_YEAR,
            "month": PAYROLL_MONTH,
        },
    )

    assert response.status_code == 401


def test_admin_can_generate_payroll(
    client,
    admin_headers,
    make_employee,
):
    make_employee()

    response = generate_payroll(client, admin_headers)

    assert response.status_code == 201

    data = response.json()
    assert data["year"] == PAYROLL_YEAR
    assert data["month"] == PAYROLL_MONTH
    assert data["status"] == "GENERATED"
    assert data["record_count"] == 1
    assert data["period_start"] == "2026-09-01"
    assert data["period_end"] == "2026-09-30"


def test_hr_can_generate_payroll(
    client,
    hr_headers,
    make_employee,
):
    make_employee()

    response = generate_payroll(client, hr_headers)

    assert response.status_code == 201
    assert response.json()["status"] == "GENERATED"


def test_employee_cannot_generate_payroll(
    client,
    employee_user,
    employee_headers,
    make_employee,
):
    make_employee(user=employee_user)

    response = generate_payroll(client, employee_headers)

    assert response.status_code == 403


def test_payroll_for_current_month_is_rejected(
    client,
    admin_headers,
):
    response = client.post(
        "/api/v1/payroll/runs/generate",
        headers=admin_headers,
        json={
            "year": 2026,
            "month": 10,
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Payroll can only be generated for a completed month"
    )


def test_duplicate_monthly_payroll_returns_conflict(
    client,
    admin_headers,
    make_employee,
):
    make_employee()

    first = generate_payroll(client, admin_headers)
    assert first.status_code == 201

    second = generate_payroll(client, admin_headers)

    assert second.status_code == 409
    assert second.json()["detail"] == (
        "Payroll has already been generated for this month"
    )


def test_employee_cannot_read_payroll_runs(
    client,
    employee_headers,
):
    response = client.get(
        "/api/v1/payroll/runs",
        headers=employee_headers,
    )

    assert response.status_code == 403


def test_admin_can_adjust_lock_and_simulate_credit(
    client,
    admin_headers,
    make_employee,
    monkeypatch,
):
    employee = make_employee()

    # Step 1: Generate the payroll run.
    generated = generate_payroll(client, admin_headers)
    assert generated.status_code == 201

    run_id = generated.json()["id"]

    # Step 2: Read the generated payroll record.
    records_response = client.get(
        f"/api/v1/payroll/runs/{run_id}/records",
        headers=admin_headers,
    )

    assert records_response.status_code == 200

    records = records_response.json()
    assert len(records) == 1
    assert records[0]["employee_id"] == employee.id

    # Step 3: Add an earning adjustment.
    adjustment_response = client.post(
        f"/api/v1/payroll/runs/{run_id}/adjustments",
        headers=admin_headers,
        json={
            "employee_id": employee.id,
            "adjustment_type": "EARNING",
            "amount": "1000.00",
            "description": "Test performance bonus",
        },
    )

    assert adjustment_response.status_code == 201
    assert adjustment_response.json()["adjustment_type"] == "EARNING"

    # Step 4: Verify adjusted gross and net salary.
    records_response = client.get(
        f"/api/v1/payroll/runs/{run_id}/records",
        headers=admin_headers,
    )

    assert records_response.status_code == 200

    record = records_response.json()[0]
    assert record["gross_salary"] == "51000.00"
    assert record["net_salary"] == "1000.00"

    # Step 5: Lock the payroll.
    lock_response = client.post(
        f"/api/v1/payroll/runs/{run_id}/lock",
        headers=admin_headers,
    )

    assert lock_response.status_code == 200
    assert lock_response.json()["status"] == "LOCKED"

    # Step 6: A locked run must reject further adjustments.
    adjustment_after_lock = client.post(
        f"/api/v1/payroll/runs/{run_id}/adjustments",
        headers=admin_headers,
        json={
            "employee_id": employee.id,
            "adjustment_type": "EARNING",
            "amount": "100.00",
            "description": "Attempt after locking",
        },
    )

    assert adjustment_after_lock.status_code == 409

    # Notifications are tested separately; avoid external email
    # side effects in this payroll API test.
    monkeypatch.setattr(
        payroll_endpoint,
        "_queue_payroll_event_safely",
        lambda **kwargs: None,
    )

    # Step 7: Simulate salary credit.
    credit_response = client.post(
        f"/api/v1/payroll/runs/{run_id}/simulate-credit",
        headers=admin_headers,
    )

    assert credit_response.status_code == 200

    # Step 8: Verify credit status on the employee payroll record.
    final_records_response = client.get(
        f"/api/v1/payroll/runs/{run_id}/records",
        headers=admin_headers,
    )

    assert final_records_response.status_code == 200

    final_record = final_records_response.json()[0]
    assert final_record["credit_status"] == "SIMULATED"
    assert final_record["simulated_credit_at"] is not None

    # Step 9: The same credit must not be simulated twice.
    repeated_credit = client.post(
        f"/api/v1/payroll/runs/{run_id}/simulate-credit",
        headers=admin_headers,
    )

    assert repeated_credit.status_code == 409
    assert repeated_credit.json()["detail"] == (
        "Salary credit was already simulated"
    )


def test_employee_can_read_own_payroll(
    client,
    admin_headers,
    employee_user,
    employee_headers,
    make_employee,
):
    make_employee(user=employee_user)

    generated = generate_payroll(client, admin_headers)
    assert generated.status_code == 201

    response = client.get(
        "/api/v1/payroll/me",
        headers=employee_headers,
    )

    assert response.status_code == 200

    records = response.json()
    assert len(records) == 1
    assert records[0]["employee_email"] == employee_user.email
    assert records[0]["year"] == PAYROLL_YEAR
    assert records[0]["month"] == PAYROLL_MONTH


def test_employee_without_profile_cannot_read_own_payroll(
    client,
    employee_headers,
):
    response = client.get(
        "/api/v1/payroll/me",
        headers=employee_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Employee profile is not configured for this account"
    )


def test_payroll_run_not_found(
    client,
    admin_headers,
):
    response = client.get(
        "/api/v1/payroll/runs/99999",
        headers=admin_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Payroll run not found"