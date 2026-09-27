import logging
import math
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.planned_route import PlannedRoute
from app.models.route_deviation import RouteDeviationState
from app.models.telemetry import Telemetry
from app.models.vehicle import Vehicle
from app.services.email_service import send_route_deviation_alert


logger = logging.getLogger(__name__)
METERS_PER_DEGREE_LATITUDE = 111_320.0


def _project(latitude: float, longitude: float, reference_latitude: float) -> tuple[float, float]:
    return (
        longitude * METERS_PER_DEGREE_LATITUDE * math.cos(math.radians(reference_latitude)),
        latitude * METERS_PER_DEGREE_LATITUDE,
    )


def _point_to_segment_distance(
    point: tuple[float, float],
    start: tuple[float, float],
    end: tuple[float, float],
) -> float:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    if dx == 0 and dy == 0:
        return math.dist(point, start)
    projection = ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / (dx * dx + dy * dy)
    projection = max(0.0, min(1.0, projection))
    closest = (start[0] + projection * dx, start[1] + projection * dy)
    return math.dist(point, closest)


def calculate_route_deviation_distance(
    latitude: float,
    longitude: float,
    route_points: list[dict[str, float]],
) -> float:
    if not route_points:
        raise ValueError("Route has no points")
    reference_latitude = latitude
    point = _project(latitude, longitude, reference_latitude)
    projected = [
        _project(item["latitude"], item["longitude"], reference_latitude)
        for item in route_points
    ]
    if len(projected) == 1:
        return math.dist(point, projected[0])
    return min(
        _point_to_segment_distance(point, start, end)
        for start, end in zip(projected, projected[1:])
    )


def process_telemetry_deviation(
    db: Session,
    telemetry: Telemetry,
    vehicle: Vehicle,
) -> None:
    try:
        route = db.execute(
            select(PlannedRoute).where(PlannedRoute.trip_id == telemetry.trip_id)
        ).scalar_one_or_none()
        if route is None:
            return

        distance = calculate_route_deviation_distance(
            telemetry.latitude,
            telemetry.longitude,
            route.route_points,
        )
        now = telemetry.recorded_at
        threshold = settings.route_deviation_threshold_meters
        state = db.execute(
            select(RouteDeviationState)
            .where(RouteDeviationState.trip_id == telemetry.trip_id)
            .with_for_update()
        ).scalar_one_or_none()
        if state is None:
            state = RouteDeviationState(
                trip_id=telemetry.trip_id,
                threshold_meters=threshold,
            )
            db.add(state)

        was_deviated = state.currently_deviated
        is_deviated = distance > threshold
        state.currently_deviated = is_deviated
        state.last_distance_meters = distance
        state.threshold_meters = threshold
        state.last_checked_at = now
        should_alert = is_deviated and not was_deviated
        if should_alert:
            state.last_alert_at = now
        db.commit()

        if should_alert:
            send_route_deviation_alert(
                trip_id=telemetry.trip_id,
                vehicle=vehicle,
                telemetry=telemetry,
                distance_meters=distance,
                threshold_meters=threshold,
                route_filename=route.original_filename,
            )
    except (SQLAlchemyError, ValueError):
        db.rollback()
        logger.exception("Route deviation evaluation failed for trip %s", telemetry.trip_id)