
from datetime import datetime, time
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Time,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Shift(Base):
    __tablename__ = "shifts"

    __table_args__ = (
        CheckConstraint(
            "shift_type IN ('GENERAL', 'NIGHT', 'FLEXIBLE', 'REMOTE')",
            name="ck_shifts_type",
        ),
        CheckConstraint(
            "break_minutes >= 0",
            name="ck_shifts_break_nonnegative",
        ),
        CheckConstraint(
            "grace_minutes >= 0",
            name="ck_shifts_grace_nonnegative",
        ),
        CheckConstraint(
            "expected_work_minutes > 0",
            name="ck_shifts_work_minutes_positive",
        ),
        CheckConstraint(
            "overtime_multiplier >= 1",
            name="ck_shifts_overtime_multiplier",
        ),
        CheckConstraint(
            "shift_type IN ('FLEXIBLE', 'REMOTE') "
            "OR (start_time IS NOT NULL AND end_time IS NOT NULL)",
            name="ck_shifts_fixed_time_required",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )

    shift_type: Mapped[str] = mapped_column(
        String(20),
        default="GENERAL",
        server_default="GENERAL",
        nullable=False,
    )

    # Flexible and remote shifts may have no fixed clock times.
    start_time: Mapped[time | None] = mapped_column(
        Time,
        nullable=True,
    )

    end_time: Mapped[time | None] = mapped_column(
        Time,
        nullable=True,
    )

    break_minutes: Mapped[int] = mapped_column(
        Integer,
        default=60,
        server_default="60",
        nullable=False,
    )

    # Allowed delay before marking check-in late.
    grace_minutes: Mapped[int] = mapped_column(
        Integer,
        default=10,
        server_default="10",
        nullable=False,
    )

    # Net expected work duration for the shift.
    expected_work_minutes: Mapped[int] = mapped_column(
        Integer,
        default=480,
        server_default="480",
        nullable=False,
    )

    overtime_multiplier: Mapped[Decimal] = mapped_column(
        Numeric(4, 2),
        default=Decimal("1.50"),
        server_default="1.50",
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
