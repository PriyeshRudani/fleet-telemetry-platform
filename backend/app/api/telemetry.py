from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.dependencies import get_db
from app.schemas.telemetry import TelemetryCreate, TelemetryResponse
from app.services.telemetry_service import ingest_telemetry


router = APIRouter(prefix="/telemetry", tags=["Telemetry"])


@router.post(
    "",
    response_model=TelemetryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_telemetry(
    telemetry_data: TelemetryCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return ingest_telemetry(db, telemetry_data, current_user)