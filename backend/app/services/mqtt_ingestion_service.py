import logging
from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.vehicle import Vehicle
from app.realtime.redis_pubsub import RedisPublisher
from app.schemas.telemetry import TelemetryCreate
from app.services.telemetry_service import ingest_telemetry


logger = logging.getLogger(__name__)


def handle_mqtt_message(
    topic: str,
    payload: Mapping[str, Any],
    redis_publisher: RedisPublisher | None = None,
) -> None:
    """Validate one MQTT message and route it through the telemetry gate."""
    topic_prefix = settings.mqtt_topic_prefix.rstrip("/")
    topic_parts = topic.split("/")
    prefix_parts = topic_prefix.split("/")
    if topic_parts[: len(prefix_parts)] != prefix_parts or len(topic_parts) != len(prefix_parts) + 1:
        logger.warning("Ignoring MQTT message on unexpected topic: %s", topic)
        return

    topic_device_id = topic_parts[-1]
    payload_device_id = payload.get("device_id")
    if payload_device_id != topic_device_id:
        logger.warning("Ignoring MQTT device/topic mismatch on %s", topic)
        return

    try:
        telemetry_data = TelemetryCreate.model_validate(payload)
    except ValidationError as error:
        logger.warning("Ignoring invalid MQTT telemetry on %s: %s", topic, error)
        return

    db = SessionLocal()
    try:
        vehicle = db.execute(
            select(Vehicle).where(Vehicle.device_id == topic_device_id)
        ).scalar_one_or_none()
        if vehicle is None:
            logger.warning("Ignoring MQTT telemetry for unknown device: %s", topic_device_id)
            return

        if telemetry_data.vehicle_id != vehicle.id:
            logger.warning("Ignoring MQTT device/vehicle mismatch for %s", topic_device_id)
            return

        telemetry = ingest_telemetry(
            db,
            telemetry_data,
            {"role": "SUPER_ADMIN"},
        )
        if redis_publisher is not None:
            redis_publisher.publish_telemetry(telemetry, topic_device_id)
        logger.debug("Stored MQTT telemetry for %s", topic_device_id)
    except Exception as error:
        db.rollback()
        logger.warning("Rejected MQTT telemetry on %s: %s", topic, error)
    finally:
        db.close()