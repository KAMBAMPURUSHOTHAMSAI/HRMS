
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SalaryComponent(Base):
    __tablename__ = "salary_components"

    __table_args__ = (
        CheckConstraint(
            "component_type IN ('EARNING', 'DEDUCTION')",
            name="ck_salary_components_type",
        ),
        CheckConstraint(
            "calculation_type IN ('FIXED', 'PERCENTAGE')",
            name="ck_salary_components_calculation",
        ),
        CheckConstraint(
            "percentage_base IN ('BASE_PAY', 'MONTHLY_SALARY')",
            name="ck_salary_components_percentage_base",
        ),
        CheckConstraint(
            "default_amount >= 0",
            name="ck_salary_components_amount_nonnegative",
        ),
        CheckConstraint(
            """
            calculation_type != 'PERCENTAGE'
            OR default_amount <= 100
            """,
            name="ck_salary_components_percentage_max",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    # Stable code used to identify the component in payroll calculations.
    code: Mapped[str] = mapped_column(
        String(40),
        unique=True,
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # EARNING or DEDUCTION.
    component_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    # FIXED amounts are currency values.
    # PERCENTAGE amounts are rates between 0 and 100.
    calculation_type: Mapped[str] = mapped_column(
        String(20),
        default="FIXED",
        server_default="FIXED",
        nullable=False,
    )

    default_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        server_default="0.00",
        nullable=False,
    )

    # Used when calculation_type is PERCENTAGE.
    percentage_base: Mapped[str] = mapped_column(
        String(20),
        default="BASE_PAY",
        server_default="BASE_PAY",
        nullable=False,
    )

    # Examples: performance bonus or overtime pay.
    # Variable components may differ between payroll periods.
    is_variable: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    is_taxable: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    created_by_user_id: Mapped[int | None] = mapped_column(
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
