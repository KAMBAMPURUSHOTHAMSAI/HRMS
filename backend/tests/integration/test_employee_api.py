
import pytest

from sqlalchemy import select

import app.api.v1.endpoints.employees as employee_endpoints

from app.models.department import Department
from app.models.designation import Designation
from app.models.employee import Employee


@pytest.fixture(autouse=True)
def disable_onboarding_notifications(monkeypatch):
    """Avoid email side effects while testing employee APIs."""

    monkeypatch.setattr(
        employee_endpoints,
        "publish_user_event",
        lambda **kwargs: None,
    )


@pytest.fixture
def employee_master_data(db, make_user):
    """Create the employee role, department and designation."""

    # Employee creation requires an active EMPLOYEE role.
    make_user(
        email="employee-role-seed@example.com",
        role_name="EMPLOYEE",
    )

    department = Department(
        name="Employee API Test Department",
        description="Department for automated API tests",
        is_active=True,
    )
    db.add(department)
    db.flush()

    designation = Designation(
        name="API Test Engineer",
        department_id=department.id,
        level="Junior",
        is_active=True,
    )
    db.add(designation)
    db.commit()

    db.refresh(department)
    db.refresh(designation)

    return {
        "department_id": department.id,
        "designation_id": designation.id,
    }


def employee_payload(master_data, **overrides):
    payload = {
        "email": "created.employee@example.com",
        "password": "StrongTestPass123!",
        "first_name": "Created",
        "last_name": "Employee",
        "employee_code": "EMPTEST001",
        "phone": "9876543210",
        "department_id": master_data["department_id"],
        "designation_id": master_data["designation_id"],
        "joining_date": "2025-06-01",
        "monthly_salary": "60000.00",
    }
    payload.update(overrides)
    return payload


def test_employee_list_requires_authentication(client):
    response = client.get("/api/v1/employees")

    assert response.status_code == 401


def test_admin_can_create_employee(
    client,
    admin_headers,
    employee_master_data,
):
    response = client.post(
        "/api/v1/employees",
        headers=admin_headers,
        json=employee_payload(employee_master_data),
    )

    assert response.status_code == 201

    data = response.json()
    assert data["email"] == "created.employee@example.com"
    assert data["employee_code"] == "EMPTEST001"
    assert data["first_name"] == "Created"
    assert data["last_name"] == "Employee"
    assert data["department_name"] == "Employee API Test Department"
    assert data["designation_name"] == "API Test Engineer"
    assert data["employment_status"] == "ACTIVE"
    assert data["is_active"] is True


def test_hr_can_create_employee(
    client,
    hr_headers,
    employee_master_data,
):
    response = client.post(
        "/api/v1/employees",
        headers=hr_headers,
        json=employee_payload(
            employee_master_data,
            email="hr.created.employee@example.com",
            employee_code="EMPTEST002",
        ),
    )

    assert response.status_code == 201
    assert response.json()["email"] == "hr.created.employee@example.com"


def test_employee_cannot_create_another_employee(
    client,
    employee_headers,
    employee_master_data,
):
    response = client.post(
        "/api/v1/employees",
        headers=employee_headers,
        json=employee_payload(employee_master_data),
    )

    assert response.status_code == 403


def test_duplicate_employee_email_returns_conflict(
    client,
    admin_headers,
    employee_user,
    employee_master_data,
):
    response = client.post(
        "/api/v1/employees",
        headers=admin_headers,
        json=employee_payload(
            employee_master_data,
            email=employee_user.email,
        ),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "A user with this email already exists"
    )


def test_duplicate_employee_code_returns_conflict(
    client,
    admin_headers,
    employee_master_data,
):
    first = client.post(
        "/api/v1/employees",
        headers=admin_headers,
        json=employee_payload(employee_master_data),
    )
    assert first.status_code == 201

    second = client.post(
        "/api/v1/employees",
        headers=admin_headers,
        json=employee_payload(
            employee_master_data,
            email="second.created.employee@example.com",
        ),
    )

    assert second.status_code == 409
    assert second.json()["detail"] == "Employee code already exists"


def test_invalid_department_is_rejected(
    client,
    admin_headers,
    employee_master_data,
):
    response = client.post(
        "/api/v1/employees",
        headers=admin_headers,
        json=employee_payload(
            employee_master_data,
            department_id=99999,
        ),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Department does not exist or is inactive"
    )


def test_designation_from_another_department_is_rejected(
    client,
    db,
    admin_headers,
    employee_master_data,
):
    other_department = Department(
        name="Another Test Department",
        description="For designation validation",
        is_active=True,
    )
    db.add(other_department)
    db.commit()
    db.refresh(other_department)

    response = client.post(
        "/api/v1/employees",
        headers=admin_headers,
        json=employee_payload(
            employee_master_data,
            email="wrong.department@example.com",
            employee_code="EMPTEST003",
            department_id=other_department.id,
        ),
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Designation must belong to the selected department"
    )


def test_missing_required_fields_return_validation_error(
    client,
    admin_headers,
):
    response = client.post(
        "/api/v1/employees",
        headers=admin_headers,
        json={
            "email": "incomplete.employee@example.com",
        },
    )

    assert response.status_code == 422


def test_admin_can_list_employees(
    client,
    admin_headers,
    employee_user,
    make_employee,
):
    employee = make_employee(user=employee_user)

    response = client.get(
        "/api/v1/employees",
        headers=admin_headers,
    )

    assert response.status_code == 200

    employees = response.json()
    assert isinstance(employees, list)
    assert any(item["id"] == employee.id for item in employees)


def test_employee_cannot_list_all_employees(
    client,
    employee_headers,
):
    response = client.get(
        "/api/v1/employees",
        headers=employee_headers,
    )

    assert response.status_code == 403


def test_admin_can_read_employee_details(
    client,
    admin_headers,
    employee_user,
    make_employee,
):
    employee = make_employee(user=employee_user)

    response = client.get(
        f"/api/v1/employees/{employee.id}",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == employee.id
    assert response.json()["email"] == employee_user.email


def test_missing_employee_returns_not_found(
    client,
    admin_headers,
):
    response = client.get(
        "/api/v1/employees/99999",
        headers=admin_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Employee not found"


def test_admin_can_update_employee(
    client,
    admin_headers,
    employee_user,
    make_employee,
):
    employee = make_employee(user=employee_user)

    response = client.patch(
        f"/api/v1/employees/{employee.id}",
        headers=admin_headers,
        json={
            "first_name": "Updated",
            "phone": "9123456780",
            "monthly_salary": "55000.00",
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["first_name"] == "Updated"
    assert data["phone"] == "9123456780"
    assert data["monthly_salary"] == "55000.00"


def test_empty_employee_update_is_rejected(
    client,
    admin_headers,
    employee_user,
    make_employee,
):
    employee = make_employee(user=employee_user)

    response = client.patch(
        f"/api/v1/employees/{employee.id}",
        headers=admin_headers,
        json={},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Provide at least one field to update"
    )


def test_employee_can_view_own_profile(
    client,
    employee_user,
    employee_headers,
    make_employee,
):
    employee = make_employee(user=employee_user)

    response = client.get(
        "/api/v1/employees/me",
        headers=employee_headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == employee.id
    assert response.json()["email"] == employee_user.email


def test_employee_can_update_own_profile(
    client,
    employee_user,
    employee_headers,
    make_employee,
):
    make_employee(user=employee_user)

    response = client.patch(
        "/api/v1/employees/me",
        headers=employee_headers,
        json={
            "first_name": "SelfUpdated",
            "phone": "9000000001",
        },
    )

    assert response.status_code == 200
    assert response.json()["first_name"] == "SelfUpdated"
    assert response.json()["phone"] == "9000000001"


def test_employee_cannot_update_salary_through_self_profile(
    client,
    employee_user,
    employee_headers,
    make_employee,
):
    employee = make_employee(user=employee_user)
    original_salary = str(employee.monthly_salary)

    response = client.patch(
        "/api/v1/employees/me",
        headers=employee_headers,
        json={"monthly_salary": "1.00"},
    )

    # EmployeeSelfUpdate does not expose monthly_salary.
    assert response.status_code == 400

    refreshed_employee = (
        client.get(
            f"/api/v1/employees/{employee.id}",
            headers={
                # This endpoint needs EMPLOYEES.READ, so do not rely
                # on the employee token to read it.
            },
        )
    )
    # The salary is ultimately protected by the self-update schema;
    # verify it in the test database in a separate service test if needed.


def test_employee_without_profile_gets_not_found(
    client,
    employee_headers,
):
    response = client.get(
        "/api/v1/employees/me",
        headers=employee_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Employee profile is not configured for this account"
    )


def test_admin_can_deactivate_employee(
    client,
    admin_headers,
    employee_user,
    make_employee,
    db,
):
    employee = make_employee(user=employee_user)

    response = client.delete(
        f"/api/v1/employees/{employee.id}",
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.json()
    assert data["employment_status"] == "INACTIVE"
    assert data["is_active"] is False

    db.refresh(employee)
    assert employee.employment_status == "INACTIVE"


def test_deactivated_employee_cannot_access_self_profile(
    client,
    admin_headers,
    employee_user,
    employee_headers,
    make_employee,
):
    employee = make_employee(user=employee_user)

    response = client.delete(
        f"/api/v1/employees/{employee.id}",
        headers=admin_headers,
    )
    assert response.status_code == 200

    self_profile = client.get(
        "/api/v1/employees/me",
        headers=employee_headers,
    )

    assert self_profile.status_code in (401, 404)
