
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CompensationHistory(Base):
    __tablename__ = "compensation_history"

    __table_args__ = (
        CheckConstraint(
            "previous_monthly_salary IS NULL OR previous_monthly_salary >= 0",
            name="ck_compensation_previous_salary_nonnegative",
        ),
        CheckConstraint(
            "new_monthly_salary > 0",
            name="ck_compensation_new_salary_positive",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_compensation_effective_dates",
        ),
        Index(
            "ix_compensation_employee_effective_dates",
            "employee_id",
            "effective_from",
            "effective_to",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    previous_monthly_salary: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    new_monthly_salary: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    effective_from: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    effective_to: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        index=True,
    )

    reason: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    revised_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
