
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.permissions import require_permissions
from app.schemas.report import (
    AttendanceReportRow,
    DashboardSummary,
    LeaveReportRow,
    PayrollReportRow,
)
from app.services.report_service import (
    export_report,
    get_attendance_report,
    get_dashboard_summary,
    get_leave_report,
    get_payroll_report,
)


router = APIRouter(
    prefix="/reports",
    tags=["Reports & Analytics"],
)


def build_export_response(
    report_type: str,
    file_format: str,
    rows: list[dict],
) -> Response:
    content, media_type, filename = export_report(
        report_type,
        file_format,
        rows,
    )

    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "private, no-store",
        },
    )


@router.get(
    "/dashboard",
    response_model=DashboardSummary,
)
def dashboard_summary(
    db: Session = Depends(get_db),
    _user=Depends(require_permissions("REPORTS.DASHBOARD")),
):
    return get_dashboard_summary(db)


@router.get(
    "/attendance",
    response_model=list[AttendanceReportRow],
)
def attendance_report(
    start_date: date | None = None,
    end_date: date | None = None,
    department_id: int | None = Query(default=None, gt=0),
    employee_id: int | None = Query(default=None, gt=0),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=500, ge=1, le=5000),
    db: Session = Depends(get_db),
    _user=Depends(require_permissions("REPORTS.ATTENDANCE_READ")),
):
    return get_attendance_report(
        db,
        start_date,
        end_date,
        department_id,
        employee_id,
        skip,
        limit,
    )


@router.get("/attendance/export")
def export_attendance_report(
    file_format: Literal["csv", "pdf"] = "csv",
    start_date: date | None = None,
    end_date: date | None = None,
    department_id: int | None = Query(default=None, gt=0),
    employee_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    _user=Depends(require_permissions("REPORTS.ATTENDANCE_EXPORT")),
):
    rows = get_attendance_report(
        db,
        start_date,
        end_date,
        department_id,
        employee_id,
        0,
        5000,
    )

    return build_export_response(
        "attendance",
        file_format,
        rows,
    )


@router.get(
    "/leaves",
    response_model=list[LeaveReportRow],
)
def leave_report(
    start_date: date | None = None,
    end_date: date | None = None,
    department_id: int | None = Query(default=None, gt=0),
    leave_status: Literal[
        "PENDING", "APPROVED", "REJECTED", "CANCELLED"
    ] | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=500, ge=1, le=5000),
    db: Session = Depends(get_db),
    _user=Depends(require_permissions("REPORTS.LEAVES_READ")),
):
    return get_leave_report(
        db,
        start_date,
        end_date,
        department_id,
        leave_status,
        skip,
        limit,
    )


@router.get("/leaves/export")
def export_leave_report(
    file_format: Literal["csv", "pdf"] = "csv",
    start_date: date | None = None,
    end_date: date | None = None,
    department_id: int | None = Query(default=None, gt=0),
    leave_status: Literal[
        "PENDING", "APPROVED", "REJECTED", "CANCELLED"
    ] | None = None,
    db: Session = Depends(get_db),
    _user=Depends(require_permissions("REPORTS.LEAVES_EXPORT")),
):
    rows = get_leave_report(
        db,
        start_date,
        end_date,
        department_id,
        leave_status,
        0,
        5000,
    )

    return build_export_response(
        "leaves",
        file_format,
        rows,
    )


@router.get(
    "/payroll",
    response_model=list[PayrollReportRow],
)
def payroll_report(
    year: int | None = Query(default=None, ge=2000, le=2100),
    month: int | None = Query(default=None, ge=1, le=12),
    department_id: int | None = Query(default=None, gt=0),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=500, ge=1, le=5000),
    db: Session = Depends(get_db),
    _user=Depends(require_permissions("REPORTS.PAYROLL_READ")),
):
    return get_payroll_report(
        db,
        year,
        month,
        department_id,
        skip,
        limit,
    )


@router.get("/payroll/export")
def export_payroll_report(
    file_format: Literal["csv", "pdf"] = "csv",
    year: int | None = Query(default=None, ge=2000, le=2100),
    month: int | None = Query(default=None, ge=1, le=12),
    department_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    _user=Depends(require_permissions("REPORTS.PAYROLL_EXPORT")),
):
    rows = get_payroll_report(
        db,
        year,
        month,
        department_id,
        0,
        5000,
    )

    return build_export_response(
        "payroll",
        file_format,
        rows,
    )
