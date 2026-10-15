
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class HolidaySelection(Base):
    __tablename__ = "holiday_selections"

    __table_args__ = (
        UniqueConstraint(
            "employee_id",
            "holiday_id",
            name="uq_holiday_selection_employee_holiday",
        ),
        CheckConstraint(
            "status IN ('SELECTED', 'CANCELLED')",
            name="ck_holiday_selection_status",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    holiday_id: Mapped[int] = mapped_column(
        ForeignKey("holidays.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        default="SELECTED",
        server_default="SELECTED",
        nullable=False,
    )

    selected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
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
