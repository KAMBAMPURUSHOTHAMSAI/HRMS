
from datetime import date, datetime, time
from decimal import Decimal

import pytest

from app.models.attendance import Attendance
from app.models.leave_request import LeaveRequest
from app.models.leave_type import LeaveType
from app.services import payroll_service


REPORT_YEAR = 2026
REPORT_MONTH = 9


@pytest.fixture(autouse=True)
def freeze_report_payroll_clock(monkeypatch):
    """Use a completed payroll period in these report tests."""

    monkeypatch.setattr(
        payroll_service,
        "company_today",
        lambda: date(2026, 10, 13),
    )


def create_attendance(db, employee, attendance_date):
    record = Attendance(
        employee_id=employee.id,
        attendance_date=attendance_date,
        check_in=datetime.combine(
            attendance_date,
            time(9, 0),
        ),
        check_out=datetime.combine(
            attendance_date,
            time(17, 0),
        ),
        working_minutes=480,
        status="PRESENT",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def create_leave_request(
    db,
    employee,
    *,
    start_date=date(2026, 9, 14),
    end_date=date(2026, 9, 15),
    status="APPROVED",
):
    leave_type = LeaveType(
        code="CASUAL",
        name="Casual Leave",
        description="Leave type for report tests",
        is_paid=True,
        annual_quota=Decimal("12.00"),
        is_active=True,
    )
    db.add(leave_type)
    db.flush()

    leave = LeaveRequest(
        employee_id=employee.id,
        leave_type_id=leave_type.id,
        start_date=start_date,
        end_date=end_date,
        total_days=Decimal("2.00"),
        reason="Report test leave",
        status=status,
    )
    db.add(leave)
    db.commit()
    db.refresh(leave)
    return leave


def create_payroll_report_data(db, admin_user, make_employee):
    """Generate September payroll for the report endpoint."""

    employee = make_employee(
        joining_date=date(2024, 1, 1),
        monthly_salary=Decimal("50000.00"),
    )

    run = payroll_service.generate_payroll_run(
        db,
        REPORT_YEAR,
        REPORT_MONTH,
        admin_user,
    )

    return employee, run


def test_dashboard_requires_authentication(client):
    response = client.get("/api/v1/reports/dashboard")

    assert response.status_code == 401


def test_admin_can_view_dashboard_summary(
    client,
    admin_headers,
    make_employee,
):
    make_employee()

    response = client.get(
        "/api/v1/reports/dashboard",
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.json()
    assert data["active_employees"] == 1
    assert "today_attendance_records" in data
    assert "pending_leave_requests" in data
    assert "current_month_net_payroll" in data


def test_employee_cannot_view_administrative_dashboard(
    client,
    employee_headers,
):
    response = client.get(
        "/api/v1/reports/dashboard",
        headers=employee_headers,
    )

    assert response.status_code == 403


def test_attendance_report_returns_employee_records(
    client,
    db,
    admin_headers,
    make_employee,
):
    employee = make_employee()
    first = create_attendance(
        db,
        employee,
        date(2026, 9, 10),
    )

    response = client.get(
        "/api/v1/reports/attendance",
        headers=admin_headers,
        params={
            "start_date": "2026-09-01",
            "end_date": "2026-09-30",
            "employee_id": employee.id,
        },
    )

    assert response.status_code == 200

    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["id"] == first.id
    assert rows[0]["employee_code"] == employee.employee_code
    assert rows[0]["attendance_date"] == "2026-09-10"
    assert rows[0]["status"] == "PRESENT"
    assert rows[0]["working_minutes"] == 480


def test_attendance_report_filters_by_date_and_employee(
    client,
    db,
    admin_headers,
    make_employee,
):
    employee = make_employee()

    create_attendance(db, employee, date(2026, 9, 10))
    create_attendance(db, employee, date(2026, 9, 20))

    response = client.get(
        "/api/v1/reports/attendance",
        headers=admin_headers,
        params={
            "start_date": "2026-09-15",
            "end_date": "2026-09-25",
            "employee_id": employee.id,
        },
    )

    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["attendance_date"] == "2026-09-20"


def test_attendance_report_rejects_invalid_date_range(
    client,
    admin_headers,
):
    response = client.get(
        "/api/v1/reports/attendance",
        headers=admin_headers,
        params={
            "start_date": "2026-09-25",
            "end_date": "2026-09-01",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "start_date cannot be after end_date"
    )


def test_employee_cannot_read_attendance_report(
    client,
    employee_headers,
):
    response = client.get(
        "/api/v1/reports/attendance",
        headers=employee_headers,
    )

    assert response.status_code == 403


@pytest.mark.parametrize(
    ("file_format", "content_type", "signature"),
    [
        ("csv", "text/csv", b""),
        ("pdf", "application/pdf", b"%PDF-"),
    ],
)
def test_attendance_report_export(
    client,
    db,
    admin_headers,
    make_employee,
    file_format,
    content_type,
    signature,
):
    employee = make_employee()
    create_attendance(db, employee, date(2026, 9, 10))

    response = client.get(
        "/api/v1/reports/attendance/export",
        headers=admin_headers,
        params={
            "file_format": file_format,
            "start_date": "2026-09-01",
            "end_date": "2026-09-30",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(content_type)
    assert "attachment;" in response.headers["content-disposition"]
    assert "Cache-Control" in response.headers

    if file_format == "csv":
        assert b"Employee Code" in response.content
        assert employee.employee_code.encode() in response.content
    else:
        assert response.content.startswith(signature)


def test_attendance_export_rejects_unsupported_format(
    client,
    admin_headers,
):
    response = client.get(
        "/api/v1/reports/attendance/export",
        headers=admin_headers,
        params={"file_format": "xlsx"},
    )

    assert response.status_code == 422


def test_leave_report_returns_and_filters_leave_requests(
    client,
    db,
    admin_headers,
    make_employee,
):
    employee = make_employee()

    leave = create_leave_request(
        db,
        employee,
        status="APPROVED",
    )

    response = client.get(
        "/api/v1/reports/leaves",
        headers=admin_headers,
        params={
            "leave_status": "APPROVED",
            "department_id": employee.department_id,
            "start_date": "2026-09-01",
            "end_date": "2026-09-30",
        },
    )

    assert response.status_code == 200

    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["id"] == leave.id
    assert rows[0]["employee_code"] == employee.employee_code
    assert rows[0]["leave_type"] == "Casual Leave"
    assert rows[0]["status"] == "APPROVED"


def test_leave_report_status_filter_excludes_other_statuses(
    client,
    db,
    admin_headers,
    make_employee,
):
    employee = make_employee()

    create_leave_request(
        db,
        employee,
        status="PENDING",
    )

    response = client.get(
        "/api/v1/reports/leaves",
        headers=admin_headers,
        params={"leave_status": "APPROVED"},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_employee_cannot_read_leave_report(
    client,
    employee_headers,
):
    response = client.get(
        "/api/v1/reports/leaves",
        headers=employee_headers,
    )

    assert response.status_code == 403


@pytest.mark.parametrize(
    ("file_format", "content_type", "signature"),
    [
        ("csv", "text/csv", b""),
        ("pdf", "application/pdf", b"%PDF-"),
    ],
)
def test_leave_report_export(
    client,
    db,
    admin_headers,
    make_employee,
    file_format,
    content_type,
    signature,
):
    employee = make_employee()
    create_leave_request(db, employee)

    response = client.get(
        "/api/v1/reports/leaves/export",
        headers=admin_headers,
        params={
            "file_format": file_format,
            "leave_status": "APPROVED",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(content_type)
    assert "attachment;" in response.headers["content-disposition"]

    if file_format == "csv":
        assert b"Leave Request ID" in response.content
        assert employee.employee_code.encode() in response.content
    else:
        assert response.content.startswith(signature)


def test_payroll_report_filters_by_year_month_and_department(
    client,
    db,
    admin_user,
    admin_headers,
    make_employee,
):
    employee, run = create_payroll_report_data(
        db,
        admin_user,
        make_employee,
    )

    response = client.get(
        "/api/v1/reports/payroll",
        headers=admin_headers,
        params={
            "year": REPORT_YEAR,
            "month": REPORT_MONTH,
            "department_id": employee.department_id,
        },
    )

    assert response.status_code == 200

    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["employee_code"] == employee.employee_code
    assert rows[0]["year"] == REPORT_YEAR
    assert rows[0]["month"] == REPORT_MONTH
    assert rows[0]["credit_status"] == "PENDING"


def test_payroll_report_requires_year_when_month_is_given(
    client,
    admin_headers,
):
    response = client.get(
        "/api/v1/reports/payroll",
        headers=admin_headers,
        params={"month": REPORT_MONTH},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Provide year when filtering by month"
    )


def test_employee_cannot_read_payroll_report(
    client,
    employee_headers,
):
    response = client.get(
        "/api/v1/reports/payroll",
        headers=employee_headers,
    )

    assert response.status_code == 403


@pytest.mark.parametrize(
    ("file_format", "content_type", "signature"),
    [
        ("csv", "text/csv", b""),
        ("pdf", "application/pdf", b"%PDF-"),
    ],
)
def test_payroll_report_export(
    client,
    db,
    admin_user,
    admin_headers,
    make_employee,
    file_format,
    content_type,
    signature,
):
    employee, _run = create_payroll_report_data(
        db,
        admin_user,
        make_employee,
    )

    response = client.get(
        "/api/v1/reports/payroll/export",
        headers=admin_headers,
        params={
            "file_format": file_format,
            "year": REPORT_YEAR,
            "month": REPORT_MONTH,
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(content_type)
    assert "attachment;" in response.headers["content-disposition"]

    if file_format == "csv":
        assert b"Payroll Record ID" in response.content
        assert employee.employee_code.encode() in response.content
    else:
        assert response.content.startswith(signature)


def test_employee_cannot_export_attendance_report(
    client,
    employee_headers,
):
    response = client.get(
        "/api/v1/reports/attendance/export",
        headers=employee_headers,
        params={"file_format": "csv"},
    )

    assert response.status_code == 403


def test_payroll_export_rejects_unsupported_format(
    client,
    admin_headers,
):
    response = client.get(
        "/api/v1/reports/payroll/export",
        headers=admin_headers,
        params={"file_format": "xlsx"},
    )

    assert response.status_code == 422
