import os

from sqlalchemy import select

from app.auth.security import hash_password
from app.db.session import SessionLocal
from app.models.organization import Organization
from app.models.user import User, UserRole


def required_setting(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required provisioning variable: {name}")
    return value.strip()


def main() -> None:
    db = SessionLocal()

    try:
        admin_email = required_setting("SUPER_ADMIN_EMAIL").lower()
        admin_password = required_setting("SUPER_ADMIN_PASSWORD")
        user_email = required_setting("REGULAR_USER_EMAIL").lower()
        user_password = required_setting("REGULAR_USER_PASSWORD")
        organization_id_value = os.getenv("REGULAR_USER_ORGANIZATION_ID")
        organization_name = os.getenv("REGULAR_USER_ORGANIZATION_NAME", "").strip()
        if organization_id_value:
            organization_id = int(organization_id_value)
            organization = db.get(Organization, organization_id)
            if organization is None:
                raise RuntimeError(f"Organization {organization_id} does not exist")
        elif organization_name:
            organization = db.execute(
                select(Organization).where(Organization.name == organization_name)
            ).scalar_one_or_none()
            if organization is None:
                organization = Organization(name=organization_name)
                db.add(organization)
                db.flush()
            organization_id = organization.id
        else:
            raise RuntimeError(
                "Set REGULAR_USER_ORGANIZATION_ID or REGULAR_USER_ORGANIZATION_NAME"
            )

        users_to_create = []
        if db.execute(select(User).where(User.email == admin_email)).scalar_one_or_none() is None:
            users_to_create.append(User(
                organization_id=None,
                email=admin_email,
                password_hash=hash_password(admin_password),
                role=UserRole.SUPER_ADMIN,
            ))
        if db.execute(select(User).where(User.email == user_email)).scalar_one_or_none() is None:
            users_to_create.append(User(
                organization_id=organization_id,
                email=user_email,
                password_hash=hash_password(user_password),
                role=UserRole.USER,
            ))

        db.add_all(users_to_create)
        db.commit()
        print(f"Provisioning complete; created {len(users_to_create)} user(s).")

    finally:
        db.close()


if __name__ == "__main__":
    main()