
from tests.conftest import TEST_PASSWORD


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_root_endpoint(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_login_success(client, admin_user):
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": admin_user.email,
            "password": TEST_PASSWORD,
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["access_token"]
    assert data["token_type"].lower() == "bearer"
    assert data["user"]["email"] == admin_user.email
    assert "ADMIN" in data["user"]["roles"]


def test_login_normalizes_email(client, admin_user):
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": f"  {admin_user.email.upper()}  ",
            "password": TEST_PASSWORD,
        },
    )

    assert response.status_code == 200
    assert response.json()["user"]["email"] == admin_user.email


def test_login_wrong_password(client, admin_user):
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": admin_user.email,
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401


def test_login_unknown_user(client):
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "unknown@example.com",
            "password": TEST_PASSWORD,
        },
    )

    assert response.status_code == 401


def test_inactive_user_cannot_login(client, make_user):
    inactive_user = make_user(
        email="inactive@example.com",
        role_name="EMPLOYEE",
        is_active=False,
    )

    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": inactive_user.email,
            "password": TEST_PASSWORD,
        },
    )

    assert response.status_code == 403


def test_me_requires_authentication(client):
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401


def test_me_rejects_invalid_token(client):
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401


def test_me_returns_authenticated_user(client, employee_headers, employee_user):
    response = client.get(
        "/api/v1/auth/me",
        headers=employee_headers,
    )

    assert response.status_code == 200

    data = response.json()
    assert data["email"] == employee_user.email
    assert "EMPLOYEE" in data["roles"]
