from sqlalchemy import URL, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


def _database_url() -> str | URL:
    if settings.database_url:
        database_url = settings.database_url
        if database_url.startswith("postgres://"):
            return "postgresql+psycopg://" + database_url.removeprefix("postgres://")
        if database_url.startswith("postgresql://"):
            return "postgresql+psycopg://" + database_url.removeprefix("postgresql://")
        return database_url

    return URL.create(
        drivername="postgresql+psycopg",
        username=settings.database_user,
        password=settings.database_password,
        host=settings.database_host,
        port=settings.database_port,
        database=settings.database_name,
    )


DATABASE_URL = _database_url()


engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass