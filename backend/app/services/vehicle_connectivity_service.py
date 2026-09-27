import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import update
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.vehicle import Vehicle


logger = logging.getLogger(__name__)


def mark_stale_vehicles_offline() -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(
        seconds=settings.vehicle_offline_threshold_seconds
    )
    db = SessionLocal()
    try:
        result = db.execute(
            update(Vehicle)
            .where(
                Vehicle.is_online.is_(True),
                Vehicle.last_seen_at.is_not(None),
                Vehicle.last_seen_at < cutoff,
            )
            .values(is_online=False)
        )
        db.commit()
        if result.rowcount:
            logger.info("Marked %s stale vehicle(s) offline", result.rowcount)
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Vehicle connectivity check failed")
    finally:
        db.close()