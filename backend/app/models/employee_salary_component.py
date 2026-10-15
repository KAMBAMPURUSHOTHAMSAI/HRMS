
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EmployeeSalaryComponent(Base):
    __tablename__ = "employee_salary_components"

    __table_args__ = (
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_employee_salary_components_valid_dates",
        ),
        CheckConstraint(
            "amount_override IS NULL OR amount_override >= 0",
            name="ck_employee_salary_components_amount_nonnegative",
        ),
        UniqueConstraint(
            "employee_id",
            "component_id",
            "effective_from",
            name="uq_employee_salary_component_start_date",
        ),
        Index(
            "ix_employee_salary_components_employee_dates",
            "employee_id",
            "effective_from",
            "effective_to",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    component_id: Mapped[int] = mapped_column(
        ForeignKey("salary_components.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # NULL means use the component's configured default amount.
    # For FIXED components, this is a currency amount.
    # For PERCENTAGE components, this is a percentage rate.
    amount_override: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    effective_from: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    # NULL means the assignment has no scheduled end date.
    effective_to: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
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
