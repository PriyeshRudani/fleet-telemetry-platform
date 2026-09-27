import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.dependencies import get_db
from app.models.trip import Trip, TripStatus
from app.models.telemetry import Telemetry
from app.models.vehicle import Vehicle
from app.models.planned_route import PlannedRoute
from app.models.route_deviation import RouteDeviationState
from app.core.config import settings
from app.services.route_service import MAX_KML_BYTES, parse_kml_route
from app.schemas.telemetry import HistoricalTelemetryResponse
from app.schemas.route import PlannedRouteResponse, RouteDeviationStatusResponse, RoutePoint
from app.schemas.trip import TripResponse, TripStart


router = APIRouter(prefix="/trips", tags=["Trips"])


def _visible_vehicle_filter(current_user: dict):
    if current_user.get("role") == "SUPER_ADMIN":
        return True
    return Vehicle.organization_id == current_user.get("organization_id")


def _load_visible_vehicle(
    db: Session,
    vehicle_id: int,
    current_user: dict,
) -> Vehicle:
    query = select(Vehicle).where(Vehicle.id == vehicle_id)
    visibility = _visible_vehicle_filter(current_user)
    if visibility is not True:
        query = query.where(visibility)

    vehicle = db.execute(query).scalar_one_or_none()
    if vehicle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found",
        )
    return vehicle


def _load_visible_trip(
    db: Session,
    trip_id: int,
    current_user: dict,
) -> Trip:
    query = (
        select(Trip)
        .join(Vehicle, Vehicle.id == Trip.vehicle_id)
        .where(Trip.id == trip_id)
    )
    visibility = _visible_vehicle_filter(current_user)
    if visibility is not True:
        query = query.where(visibility)

    trip = db.execute(query).scalar_one_or_none()
    if trip is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found",
        )
    return trip


@router.post(
    "/start",
    response_model=TripResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_trip(
    trip_data: TripStart,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    vehicle = _load_visible_vehicle(db, trip_data.vehicle_id, current_user)

    active_trip = db.execute(
        select(Trip).where(
            Trip.vehicle_id == vehicle.id,
            Trip.status == TripStatus.ACTIVE,
        )
    ).scalar_one_or_none()
    if active_trip is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Vehicle already has an active trip",
        )

    trip = Trip(
        vehicle_id=vehicle.id,
        started_at=datetime.now(timezone.utc),
        status=TripStatus.ACTIVE,
    )
    db.add(trip)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Vehicle already has an active trip",
        )
    db.refresh(trip)
    return trip


@router.post(
    "/{trip_id}/stop",
    response_model=TripResponse,
)
def stop_trip(
    trip_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    trip = _load_visible_trip(db, trip_id, current_user)
    if trip.status == TripStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Trip is already completed",
        )

    trip.status = TripStatus.COMPLETED
    trip.ended_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(trip)
    return trip


@router.get("", response_model=list[TripResponse])
def get_trips(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    query = select(Trip).join(Vehicle, Vehicle.id == Trip.vehicle_id)
    visibility = _visible_vehicle_filter(current_user)
    if visibility is not True:
        query = query.where(visibility)

    result = db.execute(
        query.order_by(Trip.started_at.desc(), Trip.id.desc())
    )
    return result.scalars().all()


@router.get("/{trip_id}", response_model=TripResponse)
def get_trip(
    trip_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return _load_visible_trip(db, trip_id, current_user)


@router.get(
    "/{trip_id}/telemetry",
    response_model=list[HistoricalTelemetryResponse],
)
def get_trip_telemetry(
    trip_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    _load_visible_trip(db, trip_id, current_user)

    result = db.execute(
        select(Telemetry)
        .where(Telemetry.trip_id == trip_id)
        .order_by(Telemetry.recorded_at.asc())
    )
    return result.scalars().all()


@router.get("/{trip_id}/telemetry/export")
def export_trip_telemetry(
    trip_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    _load_visible_trip(db, trip_id, current_user)

    result = db.execute(
        select(Telemetry)
        .where(Telemetry.trip_id == trip_id)
        .order_by(Telemetry.recorded_at.asc())
    )

    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow([
        "id",
        "trip_id",
        "vehicle_id",
        "recorded_at",
        "temperature",
        "humidity",
        "dew_point",
        "elevation",
        "latitude",
        "longitude",
    ])
    for telemetry in result.scalars():
        writer.writerow([
            telemetry.id,
            telemetry.trip_id,
            telemetry.vehicle_id,
            telemetry.recorded_at.isoformat(),
            telemetry.temperature,
            telemetry.humidity,
            telemetry.dew_point,
            telemetry.elevation,
            telemetry.latitude,
            telemetry.longitude,
        ])

    filename = f"trip-{trip_id}-telemetry.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(
    "/{trip_id}/route",
    response_model=PlannedRouteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_trip_route(
    trip_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    trip = _load_visible_trip(db, trip_id, current_user)
    if trip.status == TripStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Completed trips cannot receive a planned route",
        )

    filename = file.filename or "route.kml"
    if not filename.lower().endswith(".kml"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only KML route files are supported",
        )

    content = await file.read(MAX_KML_BYTES + 1)
    try:
        points = parse_kml_route(content)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    route = db.execute(
        select(PlannedRoute).where(PlannedRoute.trip_id == trip_id)
    ).scalar_one_or_none()
    if route is None:
        route = PlannedRoute(
            trip_id=trip.id,
            organization_id=_trip_organization_id(db, trip),
            original_filename=filename[:255],
            route_points=points,
        )
        db.add(route)
    else:
        route.original_filename = filename[:255]
        route.route_points = points
    db.commit()
    db.refresh(route)
    return _planned_route_response(route)


@router.get(
    "/{trip_id}/route",
    response_model=PlannedRouteResponse,
)
def get_trip_route(
    trip_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    trip = _load_visible_trip(db, trip_id, current_user)
    route = db.execute(
        select(PlannedRoute).where(PlannedRoute.trip_id == trip.id)
    ).scalar_one_or_none()
    if route is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Planned route not found",
        )
    return _planned_route_response(route)


@router.get(
    "/{trip_id}/route/status",
    response_model=RouteDeviationStatusResponse,
)
def get_trip_route_status(
    trip_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    trip = _load_visible_trip(db, trip_id, current_user)
    route = db.execute(
        select(PlannedRoute).where(PlannedRoute.trip_id == trip.id)
    ).scalar_one_or_none()
    state = db.execute(
        select(RouteDeviationState).where(RouteDeviationState.trip_id == trip.id)
    ).scalar_one_or_none()
    return RouteDeviationStatusResponse(
        has_route=route is not None,
        currently_deviated=state.currently_deviated if state else False,
        last_distance_meters=state.last_distance_meters if state else None,
        threshold_meters=state.threshold_meters if state else settings.route_deviation_threshold_meters,
        last_checked_at=state.last_checked_at if state else None,
        last_alert_at=state.last_alert_at if state else None,
    )


def _trip_organization_id(db: Session, trip: Trip) -> int:
    return db.execute(
        select(Vehicle.organization_id).where(Vehicle.id == trip.vehicle_id)
    ).scalar_one()


def _planned_route_response(route: PlannedRoute) -> PlannedRouteResponse:
    return PlannedRouteResponse(
        id=route.id,
        trip_id=route.trip_id,
        filename=route.original_filename,
        route_format="KML",
        points=[RoutePoint.model_validate(point) for point in route.route_points],
        point_count=len(route.route_points),
        uploaded_at=route.created_at,
    )