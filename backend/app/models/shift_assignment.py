
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ShiftAssignment(Base):
    __tablename__ = "shift_assignments"

    __table_args__ = (
        # Each assignment targets either an employee or a department.
        CheckConstraint(
            """
            (
                employee_id IS NOT NULL
                AND department_id IS NULL
            )
            OR
            (
                employee_id IS NULL
                AND department_id IS NOT NULL
            )
            """,
            name="ck_shift_assignments_single_target",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_shift_assignments_valid_dates",
        ),
        Index(
            "ix_shift_assignments_employee_dates",
            "employee_id",
            "effective_from",
            "effective_to",
        ),
        Index(
            "ix_shift_assignments_department_dates",
            "department_id",
            "effective_from",
            "effective_to",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    shift_id: Mapped[int] = mapped_column(
        ForeignKey("shifts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Employee-specific assignments take priority over department assignments.
    employee_id: Mapped[int | None] = mapped_column(
        ForeignKey("employees.id", ondelete="RESTRICT"),
        nullable=True,
    )

    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id", ondelete="RESTRICT"),
        nullable=True,
    )

    effective_from: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    # NULL indicates an assignment that has not yet ended.
    effective_to: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    assigned_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
