from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_super_admin
from app.db.dependencies import get_db
from app.models.organization import Organization
from app.models.vehicle import Vehicle
from app.schemas.vehicle import VehicleCreate, VehicleResponse

router = APIRouter(prefix="/vehicles", tags=["Vehicles"])


@router.post("", response_model=VehicleResponse, status_code=status.HTTP_201_CREATED)
def create_vehicle(
    vehicle_data: VehicleCreate,
    organization_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_super_admin)
):
    organization = db.execute(
        select(Organization).where(Organization.id == organization_id)
    ).scalar_one_or_none()

    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    existing_vehicle = db.execute(
        select(Vehicle).where(Vehicle.device_id == vehicle_data.device_id)
    ).scalar_one_or_none()

    if existing_vehicle:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A vehicle with this device ID already exists"
        )

    vehicle = Vehicle(
        organization_id=organization_id,
        name=vehicle_data.name.strip(),
        device_id=vehicle_data.device_id.strip(),
        is_online=False,
    )

    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)

    return vehicle


@router.get("", response_model=list[VehicleResponse])
def get_vehicles(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if current_user.get("role") == "SUPER_ADMIN":
        result = db.execute(
            select(Vehicle).order_by(Vehicle.id)
        )
    else:
        organization_id = current_user.get("organization_id")

        result = db.execute(
            select(Vehicle)
            .where(Vehicle.organization_id == organization_id)
            .order_by(Vehicle.id)
        )

    return result.scalars().all()