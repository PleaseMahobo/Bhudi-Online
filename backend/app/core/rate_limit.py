from __future__ import annotations

import os
import time
from collections import defaultdict, deque

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


class RateLimitMiddleware:
    """Per-IP sliding window limiter.

    Pure ASGI middleware (not BaseHTTPMiddleware) so WebSocket upgrades
    pass through without a broken HTTP request/response cycle.
    """

    def __init__(self, app: ASGIApp, *, limit_per_minute: int | None = None):
        self.app = app
        self.limit = int(
            limit_per_minute
            if limit_per_minute is not None
            else os.getenv("RATE_LIMIT_PER_MINUTE", "120")
        )
        self.window = 60.0
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def _client_key(self, scope: Scope) -> str:
        headers = {
            k.decode("latin-1").lower(): v.decode("latin-1")
            for k, v in scope.get("headers") or []
        }
        forwarded = headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        client = scope.get("client")
        if client:
            return client[0]
        return "unknown"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path") or ""
        if path in (
            "/api/v1/health",
            "/api/v1/health/",
            "/api/v1/health/db",
            "/metrics",
            "/healthz",
        ):
            await self.app(scope, receive, send)
            return

        key = self._client_key(scope)
        now = time.monotonic()
        q = self._hits[key]
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.limit:
            response = JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded", "limit_per_minute": self.limit},
                headers={"Retry-After": "60"},
            )
            await response(scope, receive, send)
            return
        q.append(now)
        await self.app(scope, receive, send)
