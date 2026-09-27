from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RoutePoint(BaseModel):
    latitude: float
    longitude: float


class PlannedRouteResponse(BaseModel):
    id: int
    trip_id: int
    filename: str
    route_format: str
    points: list[RoutePoint]
    point_count: int
    uploaded_at: datetime


class RouteDeviationStatusResponse(BaseModel):
    has_route: bool
    currently_deviated: bool
    last_distance_meters: float | None
    threshold_meters: float
    last_checked_at: datetime | None
    last_alert_at: datetime | None

    model_config = ConfigDict(from_attributes=True)