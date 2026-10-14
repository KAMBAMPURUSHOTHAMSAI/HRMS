
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PayrollRun(Base):
    __tablename__ = "payroll_runs"

    __table_args__ = (
        UniqueConstraint("year", "month", name="uq_payroll_run_year_month"),
        CheckConstraint("month BETWEEN 1 AND 12", name="ck_payroll_run_month"),
        CheckConstraint(
            "status IN ('GENERATED', 'LOCKED')",
            name="ck_payroll_run_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)

    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)

    status: Mapped[str] = mapped_column(
        String(20),
        default="GENERATED",
        nullable=False,
        index=True,
    )

    generated_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    locked_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    locked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    records = relationship(
        "PayrollRecord",
        back_populates="payroll_run",
        cascade="all, delete-orphan",
    )
