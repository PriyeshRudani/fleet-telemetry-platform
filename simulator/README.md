# Fleet Telemetry Simulator

The simulator publishes telemetry for three configured vehicles to the shared MQTT broker.
It does not access PostgreSQL or create trips. The backend remains responsible for deciding
whether each referenced trip is active.

Update `config.json` with the real vehicle and active trip IDs before starting it.

## Run

```powershell
cd simulator
python -m pip install -r requirements.txt
python simulator.py
```

Optional environment variables are `MQTT_BROKER_HOST`, `MQTT_BROKER_PORT`,
`MQTT_TOPIC_PREFIX`, `SIMULATOR_INTERVAL_SECONDS`, and `SIMULATOR_CONFIG`.