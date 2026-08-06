from __future__ import annotations

import asyncio
from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    """Production WebSocket connection manager with channel support."""

    def __init__(self) -> None:
        self._channels: dict[str, set[WebSocket]] = {
            "alerts": set(),
            "heartbeats": set(),
            "general": set(),
        }
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, channel: str = "general") -> None:
        await websocket.accept()
        channel = channel if channel in self._channels else "general"
        async with self._lock:
            self._channels[channel].add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            for connections in self._channels.values():
                connections.discard(websocket)

    async def broadcast(self, message: dict[str, Any], channel: str = "general") -> None:
        channel = channel if channel in self._channels else "general"
        dead: list[WebSocket] = []

        async with self._lock:
            targets = list(self._channels.get(channel, set()))

        for connection in targets:
            try:
                await connection.send_json(message)
            except Exception:
                dead.append(connection)

        if dead:
            async with self._lock:
                for connection in dead:
                    for connections in self._channels.values():
                        connections.discard(connection)

    def broadcast_sync(self, message: dict[str, Any], channel: str = "general") -> None:
        """Fire-and-forget broadcast from synchronous code."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.broadcast(message, channel=channel))
        except RuntimeError:
            try:
                asyncio.run(self.broadcast(message, channel=channel))
            except Exception:
                pass

    @property
    def active_connections(self) -> list[WebSocket]:
        result: list[WebSocket] = []
        for connections in self._channels.values():
            result.extend(connections)
        return result


manager = ConnectionManager()
