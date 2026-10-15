
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Holiday(Base):
    __tablename__ = "holidays"

    __table_args__ = (
        CheckConstraint(
            "holiday_type IN ('COMPANY', 'REGIONAL', 'OPTIONAL')",
            name="ck_holidays_type",
        ),
        CheckConstraint(
            "holiday_type != 'REGIONAL' OR region IS NOT NULL",
            name="ck_holidays_regional_region",
        ),
        Index(
            "ix_holidays_date_type",
            "holiday_date",
            "holiday_type",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    holiday_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    holiday_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    # Required only for REGIONAL holidays.
    # Examples: Andhra Pradesh, Telangana, Karnataka.
    region: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
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
