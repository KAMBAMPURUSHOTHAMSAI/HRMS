
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PayrollRecord(Base):
    __tablename__ = "payroll_records"

    __table_args__ = (
        UniqueConstraint(
            "payroll_run_id",
            "employee_id",
            name="uq_payroll_record_run_employee",
        ),
        CheckConstraint(
            "monthly_salary >= 0",
            name="ck_payroll_monthly_salary",
        ),
        CheckConstraint(
            "lop_days >= 0",
            name="ck_payroll_lop_days",
        ),
        CheckConstraint(
            "net_salary >= 0",
            name="ck_payroll_net_salary",
        ),
        CheckConstraint(
            "credit_status IN ('PENDING', 'SIMULATED')",
            name="ck_payroll_credit_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    payroll_run_id: Mapped[int] = mapped_column(
        ForeignKey("payroll_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    monthly_salary: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    eligible_working_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    present_days: Mapped[Decimal] = mapped_column(
        Numeric(6, 2),
        nullable=False,
    )

    paid_leave_days: Mapped[Decimal] = mapped_column(
        Numeric(6, 2),
        nullable=False,
    )

    payable_days: Mapped[Decimal] = mapped_column(
        Numeric(6, 2),
        nullable=False,
    )

    lop_days: Mapped[Decimal] = mapped_column(
        Numeric(6, 2),
        nullable=False,
    )

    base_pay: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    lop_deduction: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    other_earnings: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        nullable=False,
    )

    other_deductions: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        nullable=False,
    )

    gross_salary: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    net_salary: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    credit_status: Mapped[str] = mapped_column(
        String(20),
        default="PENDING",
        nullable=False,
    )

    simulated_credit_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    payroll_run = relationship(
        "PayrollRun",
        back_populates="records",
    )

    employee = relationship("Employee")

    adjustments = relationship(
        "PayrollAdjustment",
        back_populates="payroll_record",
        cascade="all, delete-orphan",
    )
    salary_slip = relationship(
        "SalarySlip",
        back_populates="payroll_record",
        uselist=False,
        cascade="all, delete-orphan",
    )
