
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, backref, mapped_column, relationship

from app.db.base import Base


class PayrollComponentLine(Base):
    __tablename__ = "payroll_component_lines"

    __table_args__ = (
        CheckConstraint(
            "component_type IN ('EARNING', 'DEDUCTION')",
            name="ck_payroll_component_line_type",
        ),
        CheckConstraint(
            "amount >= 0",
            name="ck_payroll_component_line_amount",
        ),
        Index(
            "ix_payroll_component_lines_record_type",
            "payroll_record_id",
            "component_type",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    payroll_record_id: Mapped[int] = mapped_column(
        ForeignKey("payroll_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    salary_component_id: Mapped[int | None] = mapped_column(
        ForeignKey("salary_components.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    component_code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    component_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    component_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    is_taxable: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
    )

    calculation_details: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    payroll_record = relationship(
        "PayrollRecord",
        backref=backref(
            "component_lines",
            cascade="all, delete-orphan",
            order_by="PayrollComponentLine.id",
        ),
    )
