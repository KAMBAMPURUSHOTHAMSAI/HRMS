from datetime import date
from pathlib import Path

import pytest
from fastapi import HTTPException

from app.models.payroll_run import PayrollRun
from app.services import payroll_service, salary_slip_service


@pytest.fixture(autouse=True)
def isolate_salary_slip_storage(tmp_path, monkeypatch):
    """Keep generated PDF files inside the temporary test directory."""

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


def create_locked_run(db, admin_user, make_employee):
    """Generate and lock a payroll run for one test employee."""

    make_employee()

    run = payroll_service.generate_payroll_run(
        db,
        2026,
        9,
        admin_user,
    )

    return payroll_service.lock_payroll(
        db,
        run.id,
        admin_user,
    )


def test_salary_slip_pdf_has_valid_pdf_signature(
    db,
    admin_user,
    make_employee,
):
    run = create_locked_run(db, admin_user, make_employee)
    record = run.records[0]

    pdf_bytes = salary_slip_service.build_pdf(record, run)

    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 500


def test_generate_salary_slips_creates_pdf_and_database_record(
    db,
    admin_user,
    make_employee,
):
    run = create_locked_run(db, admin_user, make_employee)

    slips = salary_slip_service.generate_salary_slips(
        db,
        run.id,
        admin_user,
    )

    assert len(slips) == 1

    slip = slips[0]
    path = salary_slip_service.resolve_storage_path(
        slip.storage_path
    )

    assert slip.payroll_record_id == run.records[0].id
    assert slip.generated_by_user_id == admin_user.id
    assert slip.file_name.lower().endswith(".pdf")
    assert len(slip.sha256_hash) == 64
    assert path.is_file()
    assert path.read_bytes().startswith(b"%PDF-")


def test_repeated_generation_reuses_existing_slip(
    db,
    admin_user,
    make_employee,
):
    run = create_locked_run(db, admin_user, make_employee)

    first = salary_slip_service.generate_salary_slips(
        db,
        run.id,
        admin_user,
    )
    second = salary_slip_service.generate_salary_slips(
        db,
        run.id,
        admin_user,
    )

    assert len(first) == 1
    assert len(second) == 1
    assert second[0].id == first[0].id
    assert second[0].storage_path == first[0].storage_path


def test_salary_slips_cannot_be_generated_before_payroll_lock(
    db,
    admin_user,
    make_employee,
):
    make_employee()

    run = payroll_service.generate_payroll_run(
        db,
        2026,
        9,
        admin_user,
    )

    with pytest.raises(HTTPException) as error:
        salary_slip_service.generate_salary_slips(
            db,
            run.id,
            admin_user,
        )

    assert error.value.status_code == 409
    assert error.value.detail == (
        "Lock payroll before generating salary slips"
    )


def test_missing_payroll_run_returns_not_found(
    db,
    admin_user,
):
    with pytest.raises(HTTPException) as error:
        salary_slip_service.generate_salary_slips(
            db,
            99999,
            admin_user,
        )

    assert error.value.status_code == 404
    assert error.value.detail == "Payroll run not found"


def test_locked_payroll_without_records_is_rejected(
    db,
    admin_user,
):
    run = PayrollRun(
        year=2026,
        month=9,
        period_start=date(2026, 9, 1),
        period_end=date(2026, 9, 30),
        status="LOCKED",
        generated_by_user_id=admin_user.id,
        locked_by_user_id=admin_user.id,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    with pytest.raises(HTTPException) as error:
        salary_slip_service.generate_salary_slips(
            db,
            run.id,
            admin_user,
        )

    assert error.value.status_code == 409
    assert error.value.detail == (
        "This payroll run has no salary records"
    )


def test_missing_salary_slip_returns_not_found(db):
    with pytest.raises(HTTPException) as error:
        salary_slip_service.get_salary_slip(
            db,
            99999,
        )

    assert error.value.status_code == 404
    assert error.value.detail == "Salary slip not found"


def test_missing_pdf_file_returns_not_found(
    db,
    admin_user,
    make_employee,
):
    run = create_locked_run(db, admin_user, make_employee)

    slips = salary_slip_service.generate_salary_slips(
        db,
        run.id,
        admin_user,
    )
    slip = slips[0]

    pdf_path = salary_slip_service.resolve_storage_path(
        slip.storage_path
    )
    pdf_path.unlink()

    with pytest.raises(HTTPException) as error:
        salary_slip_service.get_salary_slip_file(slip)

    assert error.value.status_code == 404
    assert error.value.detail == "Salary slip file is not available"


def test_storage_path_traversal_is_rejected():
    with pytest.raises(HTTPException) as error:
        salary_slip_service.resolve_storage_path(
            "../outside.pdf"
        )

    assert error.value.status_code == 500
    assert error.value.detail == "Invalid salary slip storage path"