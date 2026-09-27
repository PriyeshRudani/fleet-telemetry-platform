from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_super_admin
from app.db.dependencies import get_db
from app.models.organization import Organization
from app.schemas.organization import OrganizationCreate, OrganizationResponse


router = APIRouter(
    prefix="/organizations",
    tags=["Organizations"]
)


@router.post(
    "",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED
)
def create_organization(
    organization_data: OrganizationCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_super_admin)
):
    organization = Organization(
        name=organization_data.name.strip()
    )

    db.add(organization)
    db.commit()
    db.refresh(organization)

    return organization