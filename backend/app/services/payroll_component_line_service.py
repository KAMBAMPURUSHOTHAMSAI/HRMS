
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.payroll_component_line import PayrollComponentLine
from app.models.payroll_record import PayrollRecord


def _get_payroll_record_or_404(
    db: Session,
    payroll_record_id: int,
) -> PayrollRecord:
    record = db.scalar(
        select(PayrollRecord)
        .where(PayrollRecord.id == payroll_record_id)
        .options(
            selectinload(PayrollRecord.payroll_run),
            selectinload(PayrollRecord.adjustments),
        )
    )

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payroll record not found",
        )

    return record


def list_payroll_component_lines(
    db: Session,
    payroll_record_id: int,
) -> list[PayrollComponentLine]:
    # Validate that the payroll record exists.
    _get_payroll_record_or_404(db, payroll_record_id)

    query = (
        select(PayrollComponentLine)
        .where(
            PayrollComponentLine.payroll_record_id
            == payroll_record_id
        )
        .order_by(PayrollComponentLine.id.asc())
    )

    return list(db.scalars(query).all())


def create_payroll_component_snapshot(
    db: Session,
    payroll_record_id: int,
) -> list[PayrollComponentLine]:
    record = _get_payroll_record_or_404(
        db,
        payroll_record_id,
    )

    # Always query the database directly.
    # Do not use record.component_lines here because an already-loaded
    # ORM relationship can contain a stale collection after inserts.
    existing_lines = list(
        db.scalars(
            select(PayrollComponentLine)
            .where(
                PayrollComponentLine.payroll_record_id
                == record.id
            )
            .order_by(PayrollComponentLine.id.asc())
        ).all()
    )

    # Existing snapshots must never be duplicated.
    if existing_lines:
        return existing_lines

    # Only GENERATED payroll runs can receive new snapshots.
    if record.payroll_run.status != "GENERATED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Cannot create a new component snapshot "
                "for a locked payroll run"
            ),
        )

    adjustments = list(record.adjustments)

    adjustment_earnings = sum(
        (
            item.amount
            for item in adjustments
            if item.adjustment_type == "EARNING"
        ),
        start=record.base_pay * 0,
    )

    adjustment_deductions = sum(
        (
            item.amount
            for item in adjustments
            if item.adjustment_type == "DEDUCTION"
        ),
        start=record.base_pay * 0,
    )

    lines: list[PayrollComponentLine] = []

    # Basic or legacy base pay.
    if record.base_pay > 0:
        lines.append(
            PayrollComponentLine(
                payroll_record_id=record.id,
                salary_component_id=None,
                component_code="BASE_PAY",
                component_name="Base Pay",
                component_type="EARNING",
                amount=record.base_pay,
                is_taxable=True,
                calculation_details=(
                    "Snapshot of PayrollRecord.base_pay"
                ),
            )
        )

    # Loss-of-pay deduction.
    if record.lop_deduction > 0:
        lines.append(
            PayrollComponentLine(
                payroll_record_id=record.id,
                salary_component_id=None,
                component_code="LOP",
                component_name="Loss of Pay Deduction",
                component_type="DEDUCTION",
                amount=record.lop_deduction,
                is_taxable=False,
                calculation_details=(
                    f"LOP days: {record.lop_days}"
                ),
            )
        )

    # Preserve individual adjustment lines.
    for adjustment in adjustments:
        lines.append(
            PayrollComponentLine(
                payroll_record_id=record.id,
                salary_component_id=None,
                component_code=f"ADJ-{adjustment.id}",
                component_name=adjustment.description[:150],
                component_type=adjustment.adjustment_type,
                amount=adjustment.amount,
                is_taxable=False,
                calculation_details=(
                    "Snapshot of an existing payroll adjustment"
                ),
            )
        )

    # Preserve earnings that do not have corresponding adjustment rows.
    if record.other_earnings > adjustment_earnings:
        lines.append(
            PayrollComponentLine(
                payroll_record_id=record.id,
                salary_component_id=None,
                component_code="OTHER_EARNINGS",
                component_name="Other Earnings",
                component_type="EARNING",
                amount=(
                    record.other_earnings - adjustment_earnings
                ),
                is_taxable=False,
                calculation_details=(
                    "Unitemized existing payroll earnings"
                ),
            )
        )

    # Preserve deductions that do not have corresponding adjustment rows.
    if record.other_deductions > adjustment_deductions:
        lines.append(
            PayrollComponentLine(
                payroll_record_id=record.id,
                salary_component_id=None,
                component_code="OTHER_DEDUCTIONS",
                component_name="Other Deductions",
                component_type="DEDUCTION",
                amount=(
                    record.other_deductions
                    - adjustment_deductions
                ),
                is_taxable=False,
                calculation_details=(
                    "Unitemized existing payroll deductions"
                ),
            )
        )

    try:
        db.add_all(lines)
        db.flush()

        # Commit the full snapshot atomically.
        db.commit()

        # Return the persisted rows in a predictable order.
        return list_payroll_component_lines(
            db=db,
            payroll_record_id=record.id,
        )

    except Exception:
        db.rollback()
        raise
