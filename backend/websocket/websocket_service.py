"""WebSocket routing and notification helpers for Cipher Frame."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies.auth_dependencies import get_current_user
from backend.models.server_log import LogLevel
from backend.models.user import User
from backend.schemas.websocket_schema import OnlineUserItem
from backend.services.log_service import create_server_log
from backend.websocket.connection_manager import ConnectionManager
from backend.services.token_service import decode_access_token
from backend.schemas.auth_schema import TokenData

router = APIRouter()
connection_manager = ConnectionManager()
_app_loop: asyncio.AbstractEventLoop | None = None


def register_event_loop(loop: asyncio.AbstractEventLoop | None) -> None:
    """Register the application loop so sync services can schedule websocket events."""

    global _app_loop
    _app_loop = loop


def _schedule_event(coro: Any) -> None:
    """Schedule an async websocket operation on the running application loop."""

    if _app_loop is None:
        return
    asyncio.run_coroutine_threadsafe(coro, _app_loop)


async def _broadcast_online_users() -> None:
    """Push the current online user registry to all connected websocket clients."""

    await connection_manager.broadcast_online_users()


async def _heartbeat(websocket: WebSocket, user_id: int) -> None:
    """Send periodic ping events to keep the websocket connection active."""

    while True:
        await asyncio.sleep(30)
        try:
            await websocket.send_json({"event": "ping", "data": {"timestamp": datetime.now(timezone.utc).isoformat()}})
            await connection_manager.touch(user_id)
        except Exception:
            break


def notify_user_event(user_id: int, event: str, data: dict[str, Any]) -> None:
    """Send a websocket event to a single user if they are connected."""

    _schedule_event(connection_manager.send_to_user(user_id, event, data))


def broadcast_event(event: str, data: dict[str, Any]) -> None:
    """Broadcast a websocket event to every connected client."""

    _schedule_event(connection_manager.broadcast_event(event, data))


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket, token: str | None = Query(default=None), db: Session = Depends(get_db)) -> None:
    """Authenticate the websocket connection and track the user in the online registry."""

    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        payload = decode_access_token(token)
        token_data = TokenData(sub=payload.get("sub"), role=payload.get("role"))
    except Exception:
        create_server_log(
            db,
            level=LogLevel.WARNING,
            event_type="invalid_websocket_token",
            message="Rejected websocket connection due to invalid token.",
        )
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    if token_data.sub is None:
        create_server_log(
            db,
            level=LogLevel.WARNING,
            event_type="invalid_websocket_token",
            message="Rejected websocket connection due to missing token subject.",
        )
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        user_id = int(token_data.sub)
    except ValueError:
        create_server_log(
            db,
            level=LogLevel.WARNING,
            event_type="invalid_websocket_token",
            message="Rejected websocket connection due to invalid token subject.",
        )
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        create_server_log(
            db,
            level=LogLevel.WARNING,
            event_type="unauthorized_websocket_access",
            message=f"Inactive or unknown user attempted websocket access user_id={token_data.sub}",
            actor_user_id=user_id,
        )
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    previous = await connection_manager.connect(websocket, user.id, user.username)
    if previous is not None:
        try:
            await previous.websocket.close(code=status.WS_1000_NORMAL_CLOSURE)
        except Exception:
            pass

    create_server_log(
        db,
        level=LogLevel.INFO,
        event_type="websocket_connected",
        message=f"Websocket connected for user_id={user.id} username={user.username}",
        actor_user_id=user.id,
    )

    await websocket.send_json(
        {
            "event": "user_connected",
            "data": {
                "user_id": user.id,
                "username": user.username,
                "connection_time": datetime.now(timezone.utc).isoformat(),
            },
        }
    )
    broadcast_event(
        "user_connected",
        {
            "user_id": user.id,
            "username": user.username,
            "connection_time": datetime.now(timezone.utc).isoformat(),
        },
    )
    await _broadcast_online_users()

    heartbeat_task = asyncio.create_task(_heartbeat(websocket, user.id))

    try:
        while True:
            message = await websocket.receive_text()
            await connection_manager.touch(user.id)
            normalized_message = message.strip().lower()
            if normalized_message == "ping":
                await websocket.send_json({"event": "pong", "data": {"timestamp": datetime.now(timezone.utc).isoformat()}})
    except WebSocketDisconnect:
        pass
    finally:
        heartbeat_task.cancel()
        await connection_manager.disconnect(user.id)
        create_server_log(
            db,
            level=LogLevel.INFO,
            event_type="websocket_disconnected",
            message=f"Websocket disconnected for user_id={user.id} username={user.username}",
            actor_user_id=user.id,
        )
        await _broadcast_online_users()
        broadcast_event(
            "user_disconnected",
            {
                "user_id": user.id,
                "username": user.username,
                "disconnected_at": datetime.now(timezone.utc).isoformat(),
            },
        )


@router.get("/api/chat/online-users", response_model=list[OnlineUserItem])
async def online_users(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Return the current online user registry."""

    return await connection_manager.get_online_users()
