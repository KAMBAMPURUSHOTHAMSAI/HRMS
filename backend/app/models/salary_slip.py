from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SalarySlip(Base):
    __tablename__ = "salary_slips"

    __table_args__ = (
        UniqueConstraint(
            "payroll_record_id",
            name="uq_salary_slip_payroll_record",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    payroll_record_id: Mapped[int] = mapped_column(
        ForeignKey("payroll_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    generated_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    file_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    storage_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    sha256_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    payroll_record = relationship(
        "PayrollRecord",
        back_populates="salary_slip",
    )

    generated_by = relationship(
        "User",
        foreign_keys=[generated_by_user_id],
    )