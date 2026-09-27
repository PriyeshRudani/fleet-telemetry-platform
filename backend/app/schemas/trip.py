from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.trip import TripStatus


class TripStart(BaseModel):
    vehicle_id: int


class TripResponse(BaseModel):
    id: int
    vehicle_id: int
    started_at: datetime
    ended_at: datetime | None
    status: TripStatus

    model_config = ConfigDict(from_attributes=True)