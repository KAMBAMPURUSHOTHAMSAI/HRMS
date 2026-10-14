
def test_unauthenticated_cannot_list_employees(client):
    response = client.get("/api/v1/employees")

    assert response.status_code == 401


def test_employee_cannot_list_all_employees(
    client,
    employee_headers,
):
    response = client.get(
        "/api/v1/employees",
        headers=employee_headers,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "You do not have the required permission."
    )


def test_hr_can_list_employees(client, hr_headers):
    response = client.get(
        "/api/v1/employees",
        headers=hr_headers,
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_admin_can_list_employees(client, admin_headers):
    response = client.get(
        "/api/v1/employees",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_employee_cannot_read_all_attendance(
    client,
    employee_headers,
):
    response = client.get(
        "/api/v1/attendance",
        headers=employee_headers,
    )

    assert response.status_code == 403


def test_hr_can_read_all_attendance(client, hr_headers):
    response = client.get(
        "/api/v1/attendance",
        headers=hr_headers,
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_admin_can_read_all_attendance(
    client,
    admin_headers,
):
    response = client.get(
        "/api/v1/attendance",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)
