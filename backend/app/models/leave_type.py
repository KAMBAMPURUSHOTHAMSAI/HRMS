from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class LeaveType(Base):
    __tablename__ = "leave_types"

    __table_args__ = (
        CheckConstraint(
            "annual_quota >= 0",
            name="ck_leave_type_quota_nonnegative",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    code: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_paid: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    annual_quota: Mapped[Decimal] = mapped_column(
        Numeric(6, 2),
        default=Decimal("0.00"),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    leave_balances = relationship(
        "LeaveBalance",
        back_populates="leave_type",
    )

    leave_requests = relationship(
        "LeaveRequest",
        back_populates="leave_type",
    )