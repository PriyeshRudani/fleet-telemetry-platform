from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class RouteDeviationState(Base):
    __tablename__ = "route_deviation_states"

    id: Mapped[int] = mapped_column(primary_key=True)

    trip_id: Mapped[int] = mapped_column(
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    currently_deviated: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    last_distance_meters: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    threshold_meters: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    last_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    last_alert_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )