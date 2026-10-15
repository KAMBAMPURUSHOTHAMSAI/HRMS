
from datetime import date, datetime
from decimal import Decimal

from app.models.attendance import Attendance
from app.models.holiday import Holiday
from app.models.holiday_selection import HolidaySelection
from app.services.attendance_service import get_my_monthly_summary


def test_monthly_summary_excludes_applicable_holidays(
    db,
    make_employee,
):
    employee = make_employee()
    employee.region = "Andhra Pradesh"

    company_holiday = Holiday(
        name="Company Holiday",
        holiday_date=date(2026, 9, 1),
        holiday_type="COMPANY",
        is_active=True,
    )

    matching_regional_holiday = Holiday(
        name="Andhra Pradesh Holiday",
        holiday_date=date(2026, 9, 2),
        holiday_type="REGIONAL",
        region="Andhra Pradesh",
        is_active=True,
    )

    other_regional_holiday = Holiday(
        name="Telangana Holiday",
        holiday_date=date(2026, 9, 3),
        holiday_type="REGIONAL",
        region="Telangana",
        is_active=True,
    )

    unselected_optional_holiday = Holiday(
        name="Unselected Optional",
        holiday_date=date(2026, 9, 4),
        holiday_type="OPTIONAL",
        is_active=True,
    )

    selected_optional_holiday = Holiday(
        name="Selected Optional",
        holiday_date=date(2026, 9, 7),
        holiday_type="OPTIONAL",
        is_active=True,
    )

    inactive_holiday = Holiday(
        name="Inactive Holiday",
        holiday_date=date(2026, 9, 8),
        holiday_type="COMPANY",
        is_active=False,
    )

    db.add_all(
        [
            company_holiday,
            matching_regional_holiday,
            other_regional_holiday,
            unselected_optional_holiday,
            selected_optional_holiday,
            inactive_holiday,
        ]
    )
    db.flush()

    db.add(
        HolidaySelection(
            employee_id=employee.id,
            holiday_id=selected_optional_holiday.id,
            status="SELECTED",
        )
    )

    # Attendance worked on a holiday is preserved.
    db.add_all(
        [
            Attendance(
                employee_id=employee.id,
                attendance_date=date(2026, 9, 1),
                check_in=datetime(2026, 9, 1, 9, 0),
                check_out=datetime(2026, 9, 1, 11, 0),
                working_minutes=120,
                status="PRESENT",
            ),
            Attendance(
                employee_id=employee.id,
                attendance_date=date(2026, 9, 9),
                check_in=datetime(2026, 9, 9, 9, 0),
                check_out=datetime(2026, 9, 9, 11, 0),
                working_minutes=120,
                status="PRESENT",
            ),
        ]
    )

    db.commit()

    summary = get_my_monthly_summary(
        db,
        employee.user,
        2026,
        9,
    )

    # Company + matching regional + selected optional.
    assert summary.holiday_days == 3

    # September 2026 has 22 weekdays; 3 are holidays.
    assert summary.scheduled_working_days == 19

    # The record on Sep 1 is still preserved.
    assert summary.days_recorded == 2
    assert summary.present_days == 2
    assert summary.total_worked_minutes == 240
    assert summary.total_worked_hours == Decimal("4.00")

    # Only Sep 9 is a non-holiday attendance record.
    assert summary.non_holiday_recorded_days == 1


def test_unselected_optional_holiday_is_not_excluded(
    db,
    make_employee,
):
    employee = make_employee()

    db.add(
        Holiday(
            name="Optional Holiday",
            holiday_date=date(2026, 9, 4),
            holiday_type="OPTIONAL",
            is_active=True,
        )
    )
    db.commit()

    summary = get_my_monthly_summary(
        db,
        employee.user,
        2026,
        9,
    )

    assert summary.holiday_days == 0
    assert summary.scheduled_working_days == 22
