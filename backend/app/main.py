import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text
from fastapi import Depends
from app.auth.dependencies import get_current_user
from app.api.auth import router as auth_router
from app.api.organizations import router as organizations_router
from app.api.telemetry import router as telemetry_router
from app.api.trips import router as trips_router
from app.api.users import router as users_router
from app.api.vehicles import router as vehicles_router
from fastapi.middleware.cors import CORSMiddleware

from app.db.session import engine
from app.mqtt.client import MQTTClient
from app.realtime.redis_pubsub import RedisPublisher
from app.realtime.websocket import router as websocket_router
from app.services.mqtt_ingestion_service import handle_mqtt_message
from app.services.vehicle_connectivity_service import mark_stale_vehicles_offline
from app.core.config import settings


async def vehicle_connectivity_monitor() -> None:
    while True:
        await asyncio.to_thread(mark_stale_vehicles_offline)
        await asyncio.sleep(settings.vehicle_offline_check_interval_seconds)


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis_publisher = RedisPublisher()
    mqtt_client = MQTTClient(
        lambda topic, payload: handle_mqtt_message(
            topic,
            payload,
            redis_publisher,
        )
    )
    mqtt_client.start()
    connectivity_task = asyncio.create_task(vehicle_connectivity_monitor())
    try:
        yield
    finally:
        connectivity_task.cancel()
        await asyncio.gather(connectivity_task, return_exceptions=True)
        mqtt_client.stop()
        redis_publisher.close()


app = FastAPI(
    title="Fleet Telemetry Platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(organizations_router)
app.include_router(users_router)
app.include_router(vehicles_router)
app.include_router(trips_router)
app.include_router(telemetry_router)
app.include_router(websocket_router)

@app.get("/protected")
def protected_route(current_user: dict = Depends(get_current_user)):
    return {
        "message": "You are authenticated",
        "user": current_user
    }

@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "fleet-telemetry-api"
    }


@app.get("/health/database")
def database_health_check():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        value = result.scalar()

    return {
        "status": "ok",
        "database": "connected",
        "test": value
    }