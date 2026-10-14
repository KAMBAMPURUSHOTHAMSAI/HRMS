
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PayrollAdjustment(Base):
    __tablename__ = "payroll_adjustments"

    __table_args__ = (
        CheckConstraint(
            "adjustment_type IN ('EARNING', 'DEDUCTION')",
            name="ck_payroll_adjustment_type",
        ),
        CheckConstraint(
            "amount > 0",
            name="ck_payroll_adjustment_amount_positive",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    payroll_record_id: Mapped[int] = mapped_column(
        ForeignKey("payroll_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    created_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    adjustment_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    payroll_record = relationship(
        "PayrollRecord",
        back_populates="adjustments",
    )
