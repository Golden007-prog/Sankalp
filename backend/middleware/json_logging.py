"""Structured JSON formatter for stdlib logging.

Cloud Logging auto-parses JSON-shaped stdout into structured fields. We
drop our well-known extras (`request_id`, `session_id`, `path`, etc.)
into top-level keys. PII redaction happens at format-time so it catches
every record regardless of which logger originated it.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from middleware.pii_redactor import redact_text

# Keys we surface from LogRecord into the JSON envelope.
_KNOWN_EXTRAS = (
    "request_id", "session_id", "path", "method", "status", "latency_ms",
    "agent", "intent", "language", "tokens_in", "tokens_out",
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "severity": record.levelname,
            "logger": record.name,
            "message": redact_text(record.getMessage()),
        }
        for key in _KNOWN_EXTRAS:
            v = getattr(record, key, None)
            if v not in (None, ""):
                payload[key] = redact_text(v) if isinstance(v, str) else v
        if record.exc_info:
            payload["exc_info"] = redact_text(self.formatException(record.exc_info))
        return json.dumps(payload, ensure_ascii=False, default=str)


def install(level: str = "INFO") -> None:
    """Replace the root logger's handlers with one JSON stdout handler."""
    root = logging.getLogger()
    root.setLevel(level.upper())
    root.handlers.clear()
    h = logging.StreamHandler()
    h.setFormatter(JsonFormatter())
    root.addHandler(h)
