import pytest

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker

import app.models
import app.core.audit_middleware as audit_middleware

from app.api.deps import get_db
from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.seed_rbac import PERMISSIONS, ROLE_PERMISSION_CODES
from app.main import app

from app.models.department import Department
from app.models.designation import Designation
from app.models.employee import Employee
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user import User
from app.models.user_role import UserRole


TEST_PASSWORD = "TestPassword123!"


@pytest.fixture
def test_database(tmp_path, monkeypatch):
    """Create a separate SQLite database for each test."""

    database_path = tmp_path / "hrms_test.sqlite3"

    test_engine = create_engine(
        URL.create(
            drivername="sqlite",
            database=str(database_path),
        ),
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )

    @event.listens_for(test_engine, "connect")
    def enable_sqlite_foreign_keys(connection, _record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=test_engine)

    TestSessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )

    # Audit middleware must use the test database as well.
    monkeypatch.setattr(
        audit_middleware,
        "SessionLocal",
        TestSessionLocal,
    )

    try:
        yield TestSessionLocal
    finally:
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()


@pytest.fixture
def db(test_database):
    """Provide a session for creating test data."""

    session = test_database()

    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(test_database):
    """Provide a test client connected to the isolated database."""

    def override_get_db():
        session = test_database()

        try:
            yield session
        finally:
            session.close()

    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)


@pytest.fixture
def make_user(db):
    """Create a user with the real RBAC permissions."""

    def _make_user(
        email="test.employee@example.com",
        role_name="EMPLOYEE",
        password=TEST_PASSWORD,
        is_active=True,
    ):
        role_name = role_name.strip().upper()

        if role_name not in ROLE_PERMISSION_CODES:
            raise ValueError(f"Unknown test role: {role_name}")

        role = db.scalar(
            select(Role).where(Role.name == role_name)
        )

        if role is None:
            role = Role(
                name=role_name,
                description=f"Test role: {role_name}",
                is_active=True,
            )
            db.add(role)
            db.flush()

        for code in ROLE_PERMISSION_CODES[role_name]:
            permission = db.scalar(
                select(Permission).where(Permission.code == code)
            )

            if permission is None:
                permission = Permission(
                    code=code,
                    description=PERMISSIONS[code],
                )
                db.add(permission)
                db.flush()

            assignment = db.get(
                RolePermission,
                (role.id, permission.id),
            )

            if assignment is None:
                db.add(
                    RolePermission(
                        role_id=role.id,
                        permission_id=permission.id,
                    )
                )

        user = User(
            email=email.strip().lower(),
            password_hash=hash_password(password),
            first_name="Test",
            last_name="User",
            is_active=is_active,
        )

        db.add(user)
        db.flush()

        db.add(
            UserRole(
                user_id=user.id,
                role_id=role.id,
            )
        )

        db.commit()
        db.refresh(user)
        return user

    return _make_user


@pytest.fixture
def admin_user(make_user):
    return make_user(
        email="test.admin@example.com",
        role_name="ADMIN",
    )


@pytest.fixture
def hr_user(make_user):
    return make_user(
        email="test.hr@example.com",
        role_name="HR",
    )


@pytest.fixture
def employee_user(make_user):
    return make_user(
        email="test.employee@example.com",
        role_name="EMPLOYEE",
    )


@pytest.fixture
def admin_headers(admin_user):
    token = create_access_token(subject=str(admin_user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def hr_headers(hr_user):
    token = create_access_token(subject=str(hr_user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def employee_headers(employee_user):
    token = create_access_token(subject=str(employee_user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def make_employee(db, make_user):
    """
    Create an employee with its user, department and designation.
    By default, it creates an EMPLOYEE role user.
    """

    def _make_employee(
        user=None,
        email=None,
        role_name="EMPLOYEE",
        employee_code=None,
        joining_date=date(2024, 1, 1),
        monthly_salary=Decimal("50000.00"),
        employment_status="ACTIVE",
    ):
        if user is None:
            last_user_id = (
                db.scalar(
                    select(User.id)
                    .order_by(User.id.desc())
                    .limit(1)
                )
                or 0
            )

            user = make_user(
                email=(
                    email
                    or f"test.employee{last_user_id + 1}@example.com"
                ),
                role_name=role_name,
            )

        if user.employee is not None:
            return user.employee

        department = db.scalar(
            select(Department).where(
                Department.name == "Test IT"
            )
        )

        if department is None:
            department = Department(
                name="Test IT",
                description="Department for automated tests",
                is_active=True,
            )
            db.add(department)
            db.flush()

        designation = db.scalar(
            select(Designation).where(
                Designation.department_id == department.id,
                Designation.name == "Test Engineer",
            )
        )

        if designation is None:
            designation = Designation(
                name="Test Engineer",
                department_id=department.id,
                level="Junior",
                is_active=True,
            )
            db.add(designation)
            db.flush()

        employee = Employee(
            user_id=user.id,
            employee_code=(
                employee_code or f"EMP-TEST-{user.id:04d}"
            ),
            department_id=department.id,
            designation_id=designation.id,
            joining_date=joining_date,
            monthly_salary=monthly_salary,
            employment_status=employment_status,
        )

        db.add(employee)
        db.commit()
        db.refresh(employee)

        return employee

    return _make_employee