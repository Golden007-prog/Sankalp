"""Structured-JSON access logging.

One log line per request: {ts, level, request_id, session_id, intent,
path, method, status, latency_ms}. Routed through stdlib logging so
PII redactor (logging.Filter) sees and scrubs it.
"""
from __future__ import annotations

import logging
import time
from typing import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

log = logging.getLogger("sankalp.access")


class JsonAccessLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        t0 = time.perf_counter()
        path = request.url.path
        method = request.method
        rid = getattr(request.state, "request_id", "no-id")
        try:
            response = await call_next(request)
        except Exception:
            log.exception(
                "request_failed",
                extra={
                    "request_id": rid, "path": path, "method": method,
                    "status": 500, "latency_ms": int((time.perf_counter() - t0) * 1000),
                },
            )
            raise
        latency_ms = int((time.perf_counter() - t0) * 1000)
        sid = response.headers.get("X-Sankalp-Session-Id", "")
        log.info(
            "request",
            extra={
                "request_id": rid,
                "session_id": sid,
                "path": path,
                "method": method,
                "status": response.status_code,
                "latency_ms": latency_ms,
            },
        )
        return response
