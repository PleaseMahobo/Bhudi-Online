from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple per-IP sliding window limiter (process-local)."""

    def __init__(self, app, *, limit_per_minute: int | None = None):
        super().__init__(app)
        self.limit = int(
            limit_per_minute
            if limit_per_minute is not None
            else os.getenv("RATE_LIMIT_PER_MINUTE", "120")
        )
        self.window = 60.0
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def _client_key(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in ("/api/v1/health", "/metrics", "/healthz"):
            return await call_next(request)

        key = self._client_key(request)
        now = time.monotonic()
        q = self._hits[key]
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded", "limit_per_minute": self.limit},
                headers={"Retry-After": "60"},
            )
        q.append(now)
        return await call_next(request)
