from __future__ import annotations

from fastapi.testclient import TestClient

from main import app


def test_mints_request_id_when_absent() -> None:
    client = TestClient(app)
    r = client.get("/api/healthz")
    rid = r.headers.get("X-Request-Id")
    assert rid and len(rid) >= 16


def test_round_trips_supplied_request_id() -> None:
    client = TestClient(app)
    r = client.get("/api/healthz", headers={"X-Request-Id": "abc-123"})
    assert r.headers["X-Request-Id"] == "abc-123"
