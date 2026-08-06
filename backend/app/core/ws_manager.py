from __future__ import annotations

import asyncio
from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    """Production WebSocket manager with channels and message batching."""

    # Flush when either limit is hit
    BATCH_MAX_SIZE = 25
    BATCH_FLUSH_INTERVAL_MS = 150

    def __init__(self) -> None:
        self._channels: dict[str, set[WebSocket]] = {
            "alerts": set(),
            "heartbeats": set(),
            "general": set(),
        }
        self._lock = asyncio.Lock()

        # Per-channel outbound queues for batching
        self._queues: dict[str, list[dict[str, Any]]] = {
            "alerts": [],
            "heartbeats": [],
            "general": [],
        }
        self._flush_tasks: dict[str, asyncio.Task | None] = {
            "alerts": None,
            "heartbeats": None,
            "general": None,
        }

    async def connect(self, websocket: WebSocket, channel: str = "general") -> None:
        await websocket.accept()
        channel = channel if channel in self._channels else "general"
        async with self._lock:
            self._channels[channel].add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            for connections in self._channels.values():
                connections.discard(websocket)

    async def broadcast(
        self,
        message: dict[str, Any],
        channel: str = "general",
        *,
        batch: bool = False,
    ) -> None:
        """
        Broadcast a message.

        batch=False  → send immediately (default, backward compatible)
        batch=True   → enqueue and flush by size or interval
        """
        channel = channel if channel in self._channels else "general"

        if not batch:
            await self._send_raw(message, channel)
            return

        async with self._lock:
            self._queues.setdefault(channel, []).append(message)
            queue_len = len(self._queues[channel])

        if queue_len >= self.BATCH_MAX_SIZE:
            await self.flush_channel(channel)
        else:
            self._schedule_flush(channel)

    def broadcast_sync(
        self,
        message: dict[str, Any],
        channel: str = "general",
        *,
        batch: bool = True,
    ) -> None:
        """
        Fire-and-forget from synchronous code.

        Defaults to batch=True for high-volume alert traffic.
        """
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.broadcast(message, channel=channel, batch=batch))
        except RuntimeError:
            try:
                asyncio.run(self.broadcast(message, channel=channel, batch=batch))
            except Exception:
                pass

    async def flush_channel(self, channel: str) -> None:
        """Flush queued messages for a channel as a single batch envelope."""
        async with self._lock:
            events = self._queues.get(channel, [])
            self._queues[channel] = []
            task = self._flush_tasks.get(channel)
            self._flush_tasks[channel] = None

        if task and not task.done():
            task.cancel()

        if not events:
            return

        # Single event — send as-is (no unnecessary envelope)
        if len(events) == 1:
            await self._send_raw(events[0], channel)
            return

        envelope = {
            "type": "batch",
            "channel": channel,
            "count": len(events),
            "events": events,
        }
        await self._send_raw(envelope, channel)

    async def flush_all(self) -> None:
        for channel in list(self._queues.keys()):
            await self.flush_channel(channel)

    def _schedule_flush(self, channel: str) -> None:
        existing = self._flush_tasks.get(channel)
        if existing and not existing.done():
            return

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return

        async def _delayed_flush() -> None:
            try:
                await asyncio.sleep(self.BATCH_FLUSH_INTERVAL_MS / 1000.0)
                await self.flush_channel(channel)
            except asyncio.CancelledError:
                pass

        self._flush_tasks[channel] = loop.create_task(_delayed_flush())

    async def _send_raw(self, message: dict[str, Any], channel: str) -> None:
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

    @property
    def active_connections(self) -> list[WebSocket]:
        result: list[WebSocket] = []
        for connections in self._channels.values():
            result.extend(connections)
        return result


manager = ConnectionManager()
