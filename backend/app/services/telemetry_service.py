from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.telemetry import Telemetry
from app.models.trip import Trip, TripStatus
from app.models.vehicle import Vehicle
from app.schemas.telemetry import TelemetryCreate
from app.services.route_deviation_service import process_telemetry_deviation


def ingest_telemetry(
    db: Session,
    telemetry_data: TelemetryCreate,
    current_user: dict,
) -> Telemetry:
    trip = db.execute(
        select(Trip).where(Trip.id == telemetry_data.trip_id)
    ).scalar_one_or_none()
    if trip is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found",
        )

    vehicle = db.execute(
        select(Vehicle).where(Vehicle.id == telemetry_data.vehicle_id)
    ).scalar_one_or_none()
    if vehicle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found",
        )

    if trip.vehicle_id != vehicle.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Telemetry vehicle does not match the trip vehicle",
        )

    if current_user.get("role") != "SUPER_ADMIN" and (
        vehicle.organization_id != current_user.get("organization_id")
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found",
        )

    if trip.status == TripStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Telemetry cannot be recorded for a completed trip",
        )

    if trip.status != TripStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Telemetry requires an active trip",
        )

    telemetry = Telemetry(
        trip_id=trip.id,
        vehicle_id=vehicle.id,
        organization_id=vehicle.organization_id,
        recorded_at=datetime.now(timezone.utc),
        temperature=telemetry_data.temperature,
        humidity=telemetry_data.humidity,
        dew_point=telemetry_data.dew_point,
        elevation=telemetry_data.elevation,
        latitude=telemetry_data.latitude,
        longitude=telemetry_data.longitude,
    )
    vehicle.is_online = True
    vehicle.last_seen_at = telemetry.recorded_at
    vehicle.latest_latitude = telemetry.latitude
    vehicle.latest_longitude = telemetry.longitude
    db.add(telemetry)
    db.commit()
    db.refresh(telemetry)
    process_telemetry_deviation(db, telemetry, vehicle)
    return telemetry