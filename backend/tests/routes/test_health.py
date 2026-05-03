"""Smoke FastAPI /api/healthz."""
from __future__ import annotations

from fastapi.testclient import TestClient

from main import app


def test_healthz_shape() -> None:
    client = TestClient(app)
    r = client.get("/api/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["service"] == "sankalp-backend"
    assert body["phase"] == "3"
    assert "X-Request-Id" in r.headers
