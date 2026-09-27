import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any

import redis.asyncio as redis_async
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.auth.security import decode_access_token
from app.core.config import settings


logger = logging.getLogger(__name__)
router = APIRouter(tags=["Realtime"])


@dataclass(frozen=True)
class ConnectionContext:
    user_id: int
    role: str
    organization_id: int | None


class ConnectionManager:
    def __init__(self):
        self._connections: dict[WebSocket, ConnectionContext] = {}

    async def connect(
        self,
        websocket: WebSocket,
        context: ConnectionContext,
    ) -> None:
        await websocket.accept()
        self._connections[websocket] = context

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.pop(websocket, None)

    async def send_json(self, websocket: WebSocket, event: dict[str, Any]) -> bool:
        try:
            await websocket.send_json(event)
            return True
        except Exception as error:
            logger.info("WebSocket send failed; removing client: %s", error)
            self.disconnect(websocket)
            return False


connection_manager = ConnectionManager()


def _authenticate_token(token: str | None) -> ConnectionContext | None:
    if not token:
        return None

    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
        role = payload["role"]
        organization_id = payload.get("organization_id")
    except (KeyError, TypeError, ValueError, Exception):
        return None

    if role == "USER":
        if organization_id is None:
            return None
        try:
            organization_id = int(organization_id)
        except (TypeError, ValueError):
            return None
    elif role == "SUPER_ADMIN":
        organization_id = None
    else:
        return None

    return ConnectionContext(
        user_id=user_id,
        role=role,
        organization_id=organization_id,
    )


def _channel_prefix() -> str:
    return settings.redis_channel_prefix.rstrip(":")


def _organization_channel(organization_id: int) -> str:
    return f"{_channel_prefix()}:org:{organization_id}"


def _organization_pattern() -> str:
    return f"{_channel_prefix()}:org:*"


def _event_is_visible(event: dict[str, Any], context: ConnectionContext) -> bool:
    if context.role == "SUPER_ADMIN":
        return True
    return event.get("organization_id") == context.organization_id


async def _subscribe(pubsub: redis_async.client.PubSub, context: ConnectionContext) -> None:
    if context.role == "SUPER_ADMIN":
        await pubsub.psubscribe(_organization_pattern())
    else:
        await pubsub.subscribe(_organization_channel(context.organization_id))


async def _wait_for_disconnect(websocket: WebSocket) -> None:
    try:
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                return
    except WebSocketDisconnect:
        return


async def _safe_close_websocket(websocket: WebSocket, code: int, reason: str) -> None:
    try:
        await websocket.close(code=code, reason=reason)
    except (WebSocketDisconnect, RuntimeError, OSError):
        logger.debug("WebSocket was already closed while sending close code %s", code)


@router.websocket("/ws/telemetry")
async def telemetry_websocket(websocket: WebSocket) -> None:
    context = _authenticate_token(websocket.query_params.get("token"))
    if context is None:
        await _safe_close_websocket(
            websocket,
            code=1008,
            reason="Invalid or missing token",
        )
        return

    await connection_manager.connect(websocket, context)
    if settings.redis_url:
        redis_client = redis_async.Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=None,
        )
    else:
        redis_client = redis_async.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password or None,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=None,
        )
    pubsub = redis_client.pubsub(ignore_subscribe_messages=True)
    redis_task: asyncio.Task | None = None
    disconnect_task: asyncio.Task | None = None

    try:
        await _subscribe(pubsub, context)
        redis_messages = pubsub.listen().__aiter__()
        redis_task = asyncio.create_task(redis_messages.__anext__())
        disconnect_task = asyncio.create_task(_wait_for_disconnect(websocket))
        while True:
            done, _ = await asyncio.wait(
                {redis_task, disconnect_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            if disconnect_task in done:
                break

            message = redis_task.result()
            redis_task = asyncio.create_task(redis_messages.__anext__())
            if message.get("type") not in {"message", "pmessage"}:
                continue

            try:
                event = json.loads(message["data"])
            except (KeyError, TypeError, json.JSONDecodeError):
                logger.warning("Ignoring malformed Redis telemetry event")
                continue

            if not isinstance(event, dict) or not _event_is_visible(event, context):
                logger.warning("Ignoring telemetry event outside WebSocket tenant scope")
                continue

            if not await connection_manager.send_json(websocket, event):
                break
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except (redis_async.RedisError, OSError, TimeoutError) as error:
        logger.warning("Redis WebSocket subscription failed: %s", error)
        await _safe_close_websocket(
            websocket,
            code=1013,
            reason="Realtime service unavailable",
        )
    finally:
        connection_tasks = [
            task
            for task in (redis_task, disconnect_task)
            if task is not None
        ]
        for task in connection_tasks:
            if not task.done():
                task.cancel()
        if connection_tasks:
            await asyncio.gather(*connection_tasks, return_exceptions=True)
        connection_manager.disconnect(websocket)
        try:
            await pubsub.aclose()
            await redis_client.aclose()
        except redis_async.RedisError as error:
            logger.debug("Redis WebSocket resource cleanup failed: %s", error)