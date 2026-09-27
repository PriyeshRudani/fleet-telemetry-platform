from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_super_admin
from app.auth.security import hash_password
from app.db.dependencies import get_db
from app.models.user import User, UserRole
from app.schemas.user import UserCreate
from app.auth.dependencies import get_current_user, require_super_admin


router = APIRouter(
    prefix="/users",
    tags=["Users"]
)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED
)
def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_super_admin)
):
    existing_user = db.execute(
        select(User).where(User.email == user_data.email)
    ).scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists"
        )

    user = User(
        organization_id=user_data.organization_id,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        role=UserRole.USER,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "id": user.id,
        "email": user.email,
        "organization_id": user.organization_id,
        "role": user.role.value,
    }

@router.get("/me")
def get_my_profile(
    current_user: dict = Depends(get_current_user)
):
    return {
        "user_id": int(current_user["sub"]),
        "role": current_user["role"],
        "organization_id": current_user["organization_id"],
    }