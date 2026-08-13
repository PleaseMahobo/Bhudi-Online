"""ASGI middleware: HTTP request metrics for Prometheus."""
from __future__ import annotations

import time
from typing import Callable

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.prometheus_metrics import observe_http


class PrometheusMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "GET")
        path = scope.get("path", "/")
        # Skip scraping /metrics itself from latency noise optional
        start = time.perf_counter()
        status_code = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message.get("status", 500))
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            if path != "/metrics":
                observe_http(method, path, status_code, time.perf_counter() - start)
