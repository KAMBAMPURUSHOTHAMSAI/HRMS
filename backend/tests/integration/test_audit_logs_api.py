from datetime import datetime, timezone

from app.models.audit_log import AuditLog


BASE_URL = "/api/v1/audit-logs"


def create_audit_log(
    db,
    *,
    actor_user_id=None,
    action="UPDATE",
    entity_type="EMPLOYEE",
    entity_id="EMP-101",
    created_at=None,
):
    log = AuditLog(
        actor_user_id=actor_user_id,
        actor_email="test@example.com",
        actor_roles="ADMIN",
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        description=f"Test audit event: {action}",
        details={"source": "automated_test"},
        ip_address="127.0.0.1",
        user_agent="pytest",
        created_at=created_at or datetime.now(timezone.utc),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def test_admin_can_list_audit_logs(
    client, db, admin_user, admin_headers
):
    first = create_audit_log(
        db, actor_user_id=admin_user.id, entity_id="EMP-101"
    )
    second = create_audit_log(
        db,
        actor_user_id=admin_user.id,
        action="CREATE",
        entity_id="EMP-102",
    )

    response = client.get(BASE_URL, headers=admin_headers)

    assert response.status_code == 200

    data = response.json()
    returned_ids = {item["id"] for item in data}

    assert first.id in returned_ids
    assert second.id in returned_ids


def test_employee_cannot_list_audit_logs(
    client, employee_headers
):
    response = client.get(BASE_URL, headers=employee_headers)

    assert response.status_code == 403


def test_admin_can_get_audit_log_details(
    client, db, admin_user, admin_headers
):
    log = create_audit_log(
        db,
        actor_user_id=admin_user.id,
        action="UPDATE",
        entity_type="EMPLOYEE",
        entity_id="EMP-201",
    )

    response = client.get(
        f"{BASE_URL}/{log.id}",
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.json()
    assert data["id"] == log.id
    assert data["action"] == "UPDATE"
    assert data["entity_type"] == "EMPLOYEE"
    assert data["entity_id"] == "EMP-201"
    assert data["description"] == "Test audit event: UPDATE"
    assert data["details"]["source"] == "automated_test"


def test_employee_cannot_get_audit_log_details(
    client, db, admin_user, employee_headers
):
    log = create_audit_log(
        db, actor_user_id=admin_user.id
    )

    response = client.get(
        f"{BASE_URL}/{log.id}",
        headers=employee_headers,
    )

    assert response.status_code == 403


def test_get_missing_audit_log_returns_404(
    client, admin_headers
):
    response = client.get(
        f"{BASE_URL}/999999",
        headers=admin_headers,
    )

    assert response.status_code == 404


def test_audit_logs_support_combined_filters(
    client, db, admin_user, employee_user, admin_headers
):
    matching = create_audit_log(
        db,
        actor_user_id=admin_user.id,
        action="UPDATE",
        entity_type="EMPLOYEE",
        entity_id="EMP-301",
    )

    create_audit_log(
        db,
        actor_user_id=employee_user.id,
        action="DELETE",
        entity_type="EMPLOYEE",
        entity_id="EMP-301",
    )

    create_audit_log(
        db,
        actor_user_id=admin_user.id,
        action="UPDATE",
        entity_type="PAYROLL",
        entity_id="PAY-301",
    )

    response = client.get(
        BASE_URL,
        params={
            "actor_user_id": admin_user.id,
            "action": "update",
            "entity_type": "EMPLOYEE",
            "entity_id": "EMP-301",
        },
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == matching.id


def test_audit_logs_support_pagination(
    client, db, admin_user, admin_headers
):
    for index in range(3):
        create_audit_log(
            db,
            actor_user_id=admin_user.id,
            entity_id=f"EMP-PAGE-{index}",
            created_at=datetime(
                2026, 10, 1 + index, 10, 0, 0, tzinfo=timezone.utc
            ),
        )

    response = client.get(
        BASE_URL,
        params={"skip": 1, "limit": 1},
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_audit_logs_support_date_range(
    client, db, admin_user, admin_headers
):
    create_audit_log(
        db,
        actor_user_id=admin_user.id,
        entity_id="EMP-BEFORE",
        created_at=datetime(
            2026, 10, 2, 10, 0, 0, tzinfo=timezone.utc
        ),
    )

    included = create_audit_log(
        db,
        actor_user_id=admin_user.id,
        entity_id="EMP-IN-RANGE",
        created_at=datetime(
            2026, 10, 8, 10, 0, 0, tzinfo=timezone.utc
        ),
    )

    create_audit_log(
        db,
        actor_user_id=admin_user.id,
        entity_id="EMP-AFTER",
        created_at=datetime(
            2026, 10, 13, 10, 0, 0, tzinfo=timezone.utc
        ),
    )

    response = client.get(
        BASE_URL,
        params={
            "start_date": "2026-10-05",
            "end_date": "2026-10-10",
        },
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == included.id


def test_audit_logs_reject_invalid_date_range(
    client, admin_headers
):
    response = client.get(
        BASE_URL,
        params={
            "start_date": "2026-10-12",
            "end_date": "2026-10-05",
        },
        headers=admin_headers,
    )

    assert response.status_code == 422


def test_audit_logs_reject_invalid_date_format(
    client, admin_headers
):
    response = client.get(
        BASE_URL,
        params={"start_date": "not-a-date"},
        headers=admin_headers,
    )

    assert response.status_code == 422


def test_audit_logs_can_filter_by_actor(
    client, db, admin_user, employee_user, admin_headers
):
    admin_log = create_audit_log(
        db,
        actor_user_id=admin_user.id,
        entity_id="ADMIN-ACTION",
    )
    create_audit_log(
        db,
        actor_user_id=employee_user.id,
        entity_id="EMPLOYEE-ACTION",
    )

    response = client.get(
        BASE_URL,
        params={"actor_user_id": admin_user.id},
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == admin_log.id
    assert data[0]["actor_user_id"] == admin_user.id


def test_audit_logs_reject_invalid_actor_id(
    client, admin_headers
):
    response = client.get(
        BASE_URL,
        params={"actor_user_id": 0},
        headers=admin_headers,
    )

    assert response.status_code == 422