"""Active WebSocket connection tracking for Cipher Frame."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
import asyncio

from fastapi import WebSocket


@dataclass
class ConnectionRecord:
    """Metadata for a single connected websocket client."""

    user_id: int
    username: str
    websocket: WebSocket
    connection_time: datetime
    last_activity: datetime


class ConnectionManager:
    """Manage active websocket connections and online user tracking."""

    def __init__(self) -> None:
        self._connections: dict[int, ConnectionRecord] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: int, username: str) -> ConnectionRecord | None:
        """Register a websocket connection and replace any stale connection for the same user."""

        previous: ConnectionRecord | None = None
        now = datetime.now(timezone.utc)
        async with self._lock:
            previous = self._connections.pop(user_id, None)
            self._connections[user_id] = ConnectionRecord(
                user_id=user_id,
                username=username,
                websocket=websocket,
                connection_time=now,
                last_activity=now,
            )
        return previous

    async def disconnect(self, user_id: int) -> ConnectionRecord | None:
        """Remove a user from the active registry."""

        async with self._lock:
            return self._connections.pop(user_id, None)

    async def touch(self, user_id: int) -> None:
        """Update the last activity timestamp for a connection."""

        async with self._lock:
            record = self._connections.get(user_id)
            if record is not None:
                record.last_activity = datetime.now(timezone.utc)

    async def get_record(self, user_id: int) -> ConnectionRecord | None:
        """Return a connection record for a connected user."""

        async with self._lock:
            return self._connections.get(user_id)

    async def get_online_users(self) -> list[dict[str, Any]]:
        """Return online users as serializable dictionaries."""

        async with self._lock:
            records = sorted(self._connections.values(), key=lambda record: record.connection_time)
            return [
                {
                    "user_id": record.user_id,
                    "username": record.username,
                    "connection_time": record.connection_time.isoformat(),
                    "last_activity": record.last_activity.isoformat(),
                }
                for record in records
            ]

    async def send_to_user(self, user_id: int, event: str, data: dict[str, Any]) -> bool:
        """Send a real-time event to a specific connected user."""

        async with self._lock:
            record = self._connections.get(user_id)
        if record is None:
            return False
        await record.websocket.send_json({"event": event, "data": data})
        return True

    async def broadcast_event(self, event: str, data: dict[str, Any]) -> None:
        """Broadcast an event to every connected user."""

        async with self._lock:
            records = list(self._connections.values())
        for record in records:
            await record.websocket.send_json({"event": event, "data": data})

    async def broadcast_online_users(self) -> None:
        """Broadcast the full online user list to all connected users."""

        await self.broadcast_event("online_users", {"users": await self.get_online_users()})
