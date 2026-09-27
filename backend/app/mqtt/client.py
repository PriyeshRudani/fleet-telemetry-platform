import json
import logging
from collections.abc import Callable
from typing import Any

import paho.mqtt.client as mqtt

from app.core.config import settings


logger = logging.getLogger(__name__)
MessageHandler = Callable[[str, dict[str, Any]], None]


class MQTTClient:
    def __init__(self, message_handler: MessageHandler):
        self._message_handler = message_handler
        self._client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id="fleet-telemetry-backend",
        )
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.on_disconnect = self._on_disconnect
        self._client.reconnect_delay_set(min_delay=1, max_delay=30)
        self._started = False

        if settings.mqtt_username:
            self._client.username_pw_set(
                settings.mqtt_username,
                settings.mqtt_password or None,
            )

    def start(self) -> None:
        if self._started:
            return

        self._started = True
        self._client.connect_async(
            settings.mqtt_broker_host,
            settings.mqtt_broker_port,
            keepalive=60,
        )
        self._client.loop_start()
        logger.info(
            "MQTT client started for %s:%s",
            settings.mqtt_broker_host,
            settings.mqtt_broker_port,
        )

    def stop(self) -> None:
        if not self._started:
            return

        self._client.disconnect()
        self._client.loop_stop()
        self._started = False
        logger.info("MQTT client stopped")

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: object,
        flags: dict[str, Any],
        reason_code: mqtt.ReasonCode,
        properties: mqtt.Properties | None,
    ) -> None:
        if reason_code.is_failure:
            logger.warning("MQTT connection failed: %s", reason_code)
            return

        topic = f"{settings.mqtt_topic_prefix.rstrip('/')}/#"
        client.subscribe(topic, qos=1)
        logger.info("Connected to MQTT broker and subscribed to %s", topic)

    def _on_disconnect(
        self,
        client: mqtt.Client,
        userdata: object,
        disconnect_flags: mqtt.DisconnectFlags,
        reason_code: mqtt.ReasonCode,
        properties: mqtt.Properties | None,
    ) -> None:
        if reason_code.value != 0:
            logger.warning("MQTT disconnected: %s; reconnecting", reason_code)

    def _on_message(
        self,
        client: mqtt.Client,
        userdata: object,
        message: mqtt.MQTTMessage,
    ) -> None:
        try:
            payload = json.loads(message.payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            logger.warning("Ignoring malformed MQTT message on %s: %s", message.topic, error)
            return

        if not isinstance(payload, dict):
            logger.warning("Ignoring non-object MQTT message on %s", message.topic)
            return

        self._message_handler(message.topic, payload)