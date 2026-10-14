from datetime import datetime, timedelta

import app.services.attendance_service as attendance_service


# Use deterministic times so the tests do not depend on the clock.
TEST_NOW = datetime(2026, 10, 13, 9, 0, 0)


def test_check_in_requires_authentication(client):
    response = client.post("/api/v1/attendance/check-in")

    assert response.status_code == 401


def test_employee_check_in_and_duplicate_check_in(
    client,
    employee_user,
    employee_headers,
    make_employee,
    monkeypatch,
):
    make_employee(user=employee_user)

    monkeypatch.setattr(
        attendance_service,
        "company_now",
        lambda: TEST_NOW,
    )

    response = client.post(
        "/api/v1/attendance/check-in",
        headers=employee_headers,
    )

    assert response.status_code == 201

    data = response.json()
    assert data["status"] == "PRESENT"
    assert data["attendance_date"] == "2026-10-13"
    assert data["employee_id"] > 0

    duplicate_response = client.post(
        "/api/v1/attendance/check-in",
        headers=employee_headers,
    )

    assert duplicate_response.status_code == 409


def test_check_out_and_monthly_summary(
    client,
    employee_user,
    employee_headers,
    make_employee,
    monkeypatch,
):
    make_employee(user=employee_user)

    monkeypatch.setattr(
        attendance_service,
        "company_now",
        lambda: TEST_NOW,
    )

    check_in_response = client.post(
        "/api/v1/attendance/check-in",
        headers=employee_headers,
    )

    assert check_in_response.status_code == 201

    monkeypatch.setattr(
        attendance_service,
        "company_now",
        lambda: TEST_NOW + timedelta(minutes=90),
    )

    check_out_response = client.post(
        "/api/v1/attendance/check-out",
        headers=employee_headers,
    )

    assert check_out_response.status_code == 200
    assert check_out_response.json()["working_minutes"] == 90

    history_response = client.get(
        "/api/v1/attendance/me",
        headers=employee_headers,
    )

    assert history_response.status_code == 200
    assert len(history_response.json()) == 1

    summary_response = client.get(
        "/api/v1/attendance/me/summary",
        params={"year": 2026, "month": 10},
        headers=employee_headers,
    )

    assert summary_response.status_code == 200

    summary = summary_response.json()
    assert summary["year"] == 2026
    assert summary["month"] == 10
    assert summary["days_recorded"] == 1
    assert summary["total_worked_minutes"] == 90
    assert float(summary["total_worked_hours"]) == 1.5


def test_employee_without_profile_gets_not_found(
    client,
    employee_headers,
):
    response = client.post(
        "/api/v1/attendance/check-in",
        headers=employee_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Employee profile is not configured for this account"
    )


def test_employee_cannot_read_all_attendance(
    client,
    employee_headers,
):
    response = client.get(
        "/api/v1/attendance",
        headers=employee_headers,
    )

    assert response.status_code == 403


def test_summary_rejects_invalid_month(
    client,
    employee_headers,
):
    response = client.get(
        "/api/v1/attendance/me/summary",
        params={"year": 2026, "month": 13},
        headers=employee_headers,
    )

    assert response.status_code == 422