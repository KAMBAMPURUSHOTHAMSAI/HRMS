from calendar import month_name
from datetime import datetime
from hashlib import sha256
from html import escape
from pathlib import Path
import re
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.employee import Employee
from app.models.payroll_record import PayrollRecord
from app.models.payroll_run import PayrollRun
from app.models.salary_slip import SalarySlip
from app.models.user import User
from app.schemas.salary_slip import SalarySlipRead


COMPANY_TIMEZONE = ZoneInfo("Asia/Kolkata")

BACKEND_DIR = Path(__file__).resolve().parents[2]
STORAGE_ROOT = BACKEND_DIR / "storage" / "salary_slips"


def money(value) -> str:
    return f"INR {value:,.2f}"


def build_pdf(record: PayrollRecord, run: PayrollRun) -> bytes:
    employee = record.employee
    user = employee.user

    styles = getSampleStyleSheet()
    buffer = __import__("io").BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f"Salary Slip - {employee.employee_code}",
        author="HRMS",
    )

    story = [
        Paragraph("HRMS — SALARY SLIP", styles["Title"]),
        Paragraph(
            f"{month_name[run.month]} {run.year}",
            styles["Heading2"],
        ),
        Spacer(1, 8 * mm),
    ]

    employee_rows = [
        ["Employee Name", escape(f"{user.first_name} {user.last_name}")],
        ["Employee Code", escape(employee.employee_code)],
        ["Email", escape(user.email)],
        ["Department", escape(employee.department.name)],
        ["Designation", escape(employee.designation.name)],
        ["Joining Date", employee.joining_date.isoformat()],
    ]

    employee_table = Table(
        employee_rows,
        colWidths=[48 * mm, 112 * mm],
    )

    employee_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
                ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )

    story.extend(
        [
            employee_table,
            Spacer(1, 8 * mm),
            Paragraph("Earnings", styles["Heading2"]),
        ]
    )

    earnings_table = Table(
        [
            ["Description", "Amount"],
            ["Base Pay", money(record.base_pay)],
            ["Other Earnings", money(record.other_earnings)],
            ["Gross Salary", money(record.gross_salary)],
        ],
        colWidths=[100 * mm, 60 * mm],
    )

    earnings_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )

    story.extend(
        [
            earnings_table,
            Spacer(1, 7 * mm),
            Paragraph("Deductions", styles["Heading2"]),
        ]
    )

    deductions_table = Table(
        [
            ["Description", "Amount"],
            ["Loss of Pay", money(record.lop_deduction)],
            ["Other Deductions", money(record.other_deductions)],
            [
                "Total Deductions",
                money(record.lop_deduction + record.other_deductions),
            ],
        ],
        colWidths=[100 * mm, 60 * mm],
    )

    deductions_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )

    story.extend(
        [
            deductions_table,
            Spacer(1, 8 * mm),
            Paragraph(
                f"<b>Net Salary: {money(record.net_salary)}</b>",
                styles["Heading2"],
            ),
            Spacer(1, 8 * mm),
            Paragraph(
                (
                    f"Attendance: {record.present_days} days | "
                    f"Paid leave: {record.paid_leave_days} days | "
                    f"LOP: {record.lop_days} days"
                ),
                styles["Normal"],
            ),
            Spacer(1, 5 * mm),
            Paragraph(
                "System-generated salary statement. "
                "No physical signature is required.",
                styles["Italic"],
            ),
        ]
    )

    document.build(story)
    return buffer.getvalue()


def resolve_storage_path(relative_path: str) -> Path:
    root = STORAGE_ROOT.resolve()
    resolved = (root / relative_path).resolve()

    if not resolved.is_relative_to(root):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invalid salary slip storage path",
        )

    return resolved


def get_slip_query():
    return select(SalarySlip).options(
        selectinload(SalarySlip.payroll_record)
        .selectinload(PayrollRecord.employee)
        .selectinload(Employee.user),
        selectinload(SalarySlip.payroll_record)
        .selectinload(PayrollRecord.employee)
        .selectinload(Employee.department),
        selectinload(SalarySlip.payroll_record)
        .selectinload(PayrollRecord.employee)
        .selectinload(Employee.designation),
        selectinload(SalarySlip.payroll_record)
        .selectinload(PayrollRecord.payroll_run),
    )


def serialize_salary_slip(slip: SalarySlip) -> SalarySlipRead:
    record = slip.payroll_record
    employee = record.employee
    user = employee.user
    run = record.payroll_run

    return SalarySlipRead(
        id=slip.id,
        payroll_record_id=record.id,
        employee_id=employee.id,
        employee_code=employee.employee_code,
        employee_name=f"{user.first_name} {user.last_name}",
        employee_email=user.email,
        year=run.year,
        month=run.month,
        file_name=slip.file_name,
        generated_at=slip.generated_at,
        net_salary=record.net_salary,
        credit_status=record.credit_status,
    )


def generate_salary_slips(
    db: Session,
    run_id: int,
    actor: User,
) -> list[SalarySlip]:
    run = db.scalar(
        select(PayrollRun)
        .where(PayrollRun.id == run_id)
        .with_for_update()
    )

    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payroll run not found",
        )

    if run.status != "LOCKED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Lock payroll before generating salary slips",
        )

    records = db.scalars(
        select(PayrollRecord)
        .where(PayrollRecord.payroll_run_id == run_id)
        .options(
            selectinload(PayrollRecord.employee)
            .selectinload(Employee.user),
            selectinload(PayrollRecord.employee)
            .selectinload(Employee.department),
            selectinload(PayrollRecord.employee)
            .selectinload(Employee.designation),
            selectinload(PayrollRecord.payroll_run),
            selectinload(PayrollRecord.salary_slip),
        )
        .order_by(PayrollRecord.employee_id)
    ).all()

    if not records:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This payroll run has no salary records",
        )

    STORAGE_ROOT.mkdir(parents=True, exist_ok=True)

    slips = []
    created_files: list[Path] = []

    try:
        for record in records:
            existing = record.salary_slip

            if existing is not None:
                existing_path = resolve_storage_path(
                    existing.storage_path
                )
                if existing_path.is_file():
                    slips.append(existing)
                    continue

            employee_code = re.sub(
                r"[^A-Za-z0-9_-]",
                "_",
                record.employee.employee_code,
            )

            relative_path = (
                Path(str(run.year))
                / f"{run.month:02d}"
                / f"salary-slip-{employee_code}-{record.id}.pdf"
            )

            target_path = resolve_storage_path(
                relative_path.as_posix()
            )

            target_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            pdf_bytes = build_pdf(record, run)
            target_path.write_bytes(pdf_bytes)
            created_files.append(target_path)

            if existing is None:
                existing = SalarySlip(
                    payroll_record_id=record.id,
                    generated_by_user_id=actor.id,
                    file_name=target_path.name,
                    storage_path=relative_path.as_posix(),
                    sha256_hash=sha256(pdf_bytes).hexdigest(),
                )
                db.add(existing)
                record.salary_slip = existing
            else:
                existing.generated_by_user_id = actor.id
                existing.file_name = target_path.name
                existing.storage_path = relative_path.as_posix()
                existing.sha256_hash = sha256(pdf_bytes).hexdigest()
                existing.generated_at = datetime.now(COMPANY_TIMEZONE)

            slips.append(existing)

        db.commit()

        for slip in slips:
            db.refresh(slip)

        return slips

    except Exception:
        db.rollback()

        for path in created_files:
            path.unlink(missing_ok=True)

        raise


def list_salary_slips(db: Session) -> list[SalarySlip]:
    statement = get_slip_query().order_by(
        SalarySlip.generated_at.desc()
    )
    return list(db.scalars(statement).all())


def list_my_salary_slips(
    db: Session,
    user: User,
) -> list[SalarySlip]:
    employee = user.employee

    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile is not configured for this account",
        )

    statement = (
        get_slip_query()
        .join(PayrollRecord)
        .where(PayrollRecord.employee_id == employee.id)
        .order_by(SalarySlip.generated_at.desc())
    )

    return list(db.scalars(statement).all())


def get_salary_slip(
    db: Session,
    slip_id: int,
) -> SalarySlip:
    slip = db.scalar(
        get_slip_query().where(SalarySlip.id == slip_id)
    )

    if slip is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salary slip not found",
        )

    return slip


def get_salary_slip_file(slip: SalarySlip) -> Path:
    path = resolve_storage_path(slip.storage_path)

    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salary slip file is not available",
        )

    return path