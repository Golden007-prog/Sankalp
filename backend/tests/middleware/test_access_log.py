"""Access-log middleware emits one structured line per request."""
from __future__ import annotations

import json
import logging

from fastapi.testclient import TestClient

from main import app


def test_access_log_emits_request_line(caplog) -> None:
    client = TestClient(app)
    with caplog.at_level(logging.INFO, logger="sankalp.access"):
        client.get("/api/healthz")
    rows = [r for r in caplog.records if r.name == "sankalp.access"]
    assert rows, "no access-log records captured"
    rec = rows[-1]
    assert getattr(rec, "path", None) == "/api/healthz"
    assert getattr(rec, "method", None) == "GET"
    assert getattr(rec, "status", None) == 200
    assert getattr(rec, "request_id", None)
