from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str | None = None
    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str = "fleet_telemetry"
    database_user: str = "postgres"
    database_password: str = ""

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    mqtt_broker_host: str = "broker.emqx.io"
    mqtt_broker_port: int = 1883
    mqtt_username: str | None = None
    mqtt_password: str | None = None
    mqtt_topic_prefix: str = "fleet/telemetry"

    redis_host: str = "127.0.0.1"
    redis_port: int = 6379
    redis_db: int = 0
    redis_url: str | None = None
    redis_password: str | None = None
    redis_channel_prefix: str = "fleet:telemetry"

    cors_allowed_origins: str = (
        "http://localhost:5173,http://localhost:5174,"
        "http://127.0.0.1:5173,http://127.0.0.1:5174"
    )

    vehicle_offline_threshold_seconds: int = 15
    vehicle_offline_check_interval_seconds: int = 5

    route_deviation_threshold_meters: float = 100.0
    email_enabled: bool = False
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str | None = None
    smtp_use_tls: bool = True
    route_alert_recipient_email: str | None = None

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )


settings = Settings()