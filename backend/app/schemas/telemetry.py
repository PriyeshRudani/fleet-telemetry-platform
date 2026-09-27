from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TelemetryCreate(BaseModel):
    trip_id: int
    vehicle_id: int
    temperature: float
    humidity: float
    dew_point: float
    elevation: float
    latitude: float
    longitude: float


class TelemetryResponse(TelemetryCreate):
    id: int
    organization_id: int
    recorded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HistoricalTelemetryResponse(BaseModel):
    id: int
    trip_id: int
    vehicle_id: int
    recorded_at: datetime
    temperature: float
    humidity: float
    dew_point: float
    elevation: float
    latitude: float
    longitude: float

    model_config = ConfigDict(from_attributes=True)