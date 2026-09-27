import json
import logging
import math
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import paho.mqtt.client as mqtt


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)

BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "broker.emqx.io")
BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
TOPIC_PREFIX = os.getenv("MQTT_TOPIC_PREFIX", "fleet/telemetry").rstrip("/")
PUBLISH_INTERVAL = float(os.getenv("SIMULATOR_INTERVAL_SECONDS", "3"))
CONFIG_PATH = Path(os.getenv("SIMULATOR_CONFIG", Path(__file__).with_name("config.json")))

ROUTES: dict[str, list[tuple[float, float]]] = {
    "vehicle-001": [(23.2156, 72.6369), (23.2190, 72.6420), (23.2240, 72.6465), (23.2200, 72.6510)],
    "vehicle-002": [(23.0300, 72.5500), (23.0340, 72.5560), (23.0390, 72.5520), (23.0430, 72.5580)],
    "vehicle-003": [(23.1000, 72.6000), (23.1040, 72.6060), (23.1090, 72.6030), (23.1130, 72.6090)],
}


@dataclass
class VehicleState:
    device_id: str
    vehicle_id: int
    trip_id: int
    route: list[tuple[float, float]]
    position: float = 0.0
    sample: int = 0

    def payload(self) -> dict[str, Any]:
        start_index = int(self.position) % len(self.route)
        end_index = (start_index + 1) % len(self.route)
        fraction = self.position - int(self.position)
        start = self.route[start_index]
        end = self.route[end_index]
        latitude = start[0] + (end[0] - start[0]) * fraction
        longitude = start[1] + (end[1] - start[1]) * fraction
        temperature = 27.0 + math.sin(self.sample / 4) * 1.5
        humidity = 63.0 + math.cos(self.sample / 5) * 4

        return {
            "device_id": self.device_id,
            "trip_id": self.trip_id,
            "vehicle_id": self.vehicle_id,
            "temperature": round(temperature, 2),
            "humidity": round(humidity, 2),
            "dew_point": round(temperature - (100 - humidity) / 5, 2),
            "elevation": round(42.0 + math.sin(self.sample / 6) * 3, 2),
            "latitude": round(latitude, 6),
            "longitude": round(longitude, 6),
        }

    def advance(self) -> None:
        self.position = (self.position + 0.25) % len(self.route)
        self.sample += 1


def load_states() -> list[VehicleState]:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    configured_vehicles = config.get("vehicles", {})
    states = []
    for device_id, route in ROUTES.items():
        vehicle_config = configured_vehicles.get(device_id)
        if not vehicle_config:
            logger.warning("Skipping %s: no vehicle_id/trip_id in %s", device_id, CONFIG_PATH)
            continue
        states.append(
            VehicleState(
                device_id=device_id,
                vehicle_id=int(vehicle_config["vehicle_id"]),
                trip_id=int(vehicle_config["trip_id"]),
                route=route,
            )
        )
    return states


def main() -> None:
    states = load_states()
    if not states:
        raise RuntimeError("No configured simulator vehicles found")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="fleet-telemetry-simulator")

    def on_connect(
        client: mqtt.Client,
        userdata: object,
        flags: dict[str, Any],
        reason_code: mqtt.ReasonCode,
        properties: mqtt.Properties | None,
    ) -> None:
        if reason_code.is_failure:
            logger.warning("MQTT connection failed: %s", reason_code)
        else:
            logger.info("Connected to MQTT broker")

    client.on_connect = on_connect
    client.reconnect_delay_set(min_delay=1, max_delay=30)
    if MQTT_USERNAME:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD or None)
    client.connect_async(BROKER_HOST, BROKER_PORT, keepalive=60)
    client.loop_start()

    try:
        while True:
            for state in states:
                topic = f"{TOPIC_PREFIX}/{state.device_id}"
                client.publish(topic, json.dumps(state.payload()), qos=1)
                logger.info("Publishing %s", state.device_id)
                state.advance()
            time.sleep(PUBLISH_INTERVAL)
    except KeyboardInterrupt:
        logger.info("Stopping simulator")
    finally:
        client.disconnect()
        client.loop_stop()


if __name__ == "__main__":
    main()