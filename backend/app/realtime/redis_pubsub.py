import json
import logging
from typing import Any

import redis

from app.core.config import settings
from app.models.telemetry import Telemetry


logger = logging.getLogger(__name__)


class RedisPublisher:
    def __init__(self, client: redis.Redis | None = None):
        self._client = client or self._create_client()

    @staticmethod
    def _create_client() -> redis.Redis:
        if settings.redis_url:
            return redis.Redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
        return redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password or None,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )

    def publish_telemetry(self, telemetry: Telemetry, device_id: str) -> bool:
        event = {
            "event": "telemetry",
            "vehicle_id": telemetry.vehicle_id,
            "device_id": device_id,
            "trip_id": telemetry.trip_id,
            "organization_id": telemetry.organization_id,
            "recorded_at": telemetry.recorded_at.isoformat(),
            "temperature": telemetry.temperature,
            "humidity": telemetry.humidity,
            "dew_point": telemetry.dew_point,
            "elevation": telemetry.elevation,
            "latitude": telemetry.latitude,
            "longitude": telemetry.longitude,
        }
        channel = (
            f"{settings.redis_channel_prefix.rstrip(':')}"
            f":org:{telemetry.organization_id}"
        )
        return self.publish(channel, event)

    def publish(self, channel: str, event: dict[str, Any]) -> bool:
        try:
            self._client.publish(channel, json.dumps(event))
            return True
        except redis.exceptions.RedisError as error:
            logger.warning("Redis publish failed for %s: %s", channel, error)
            return False

    def close(self) -> None:
        try:
            self._client.close()
        except redis.exceptions.RedisError as error:
            logger.warning("Redis close failed: %s", error)