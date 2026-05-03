"""Verify PII redactor scrubs known-sensitive values from log output."""
from __future__ import annotations

import io
import json
import logging

from middleware.json_logging import JsonFormatter
from middleware.pii_redactor import REDACTED, redact_text


def test_redact_text_basic() -> None:
    s = "user EPIC ABC1234567 mobile +91-9876543210 email rohan@example.com"
    out = redact_text(s)
    assert "ABC1234567" not in out
    assert "9876543210" not in out
    assert "rohan@example.com" not in out
    assert REDACTED in out


def _log_to_string(record: logging.LogRecord) -> str:
    buf = io.StringIO()
    h = logging.StreamHandler(buf)
    h.setFormatter(JsonFormatter())
    h.emit(record)
    return buf.getvalue()


def test_json_formatter_redacts_message() -> None:
    rec = logging.LogRecord(
        name="t", level=logging.INFO, pathname=__file__, lineno=1,
        msg="user EPIC ABC1234567 logged in", args=(), exc_info=None,
    )
    out = _log_to_string(rec)
    payload = json.loads(out)
    assert "ABC1234567" not in payload["message"]
    assert REDACTED in payload["message"]
