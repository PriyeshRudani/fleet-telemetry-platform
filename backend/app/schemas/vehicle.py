from datetime import datetime

from pydantic import BaseModel, ConfigDict


class VehicleCreate(BaseModel):
    name: str
    device_id: str


class VehicleResponse(BaseModel):
    id: int
    organization_id: int
    name: str
    device_id: str
    is_online: bool
    latest_latitude: float | None
    latest_longitude: float | None
    last_seen_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)