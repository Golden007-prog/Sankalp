from __future__ import annotations

from fastapi.testclient import TestClient

from main import app


def test_constituency_happy_path() -> None:
    client = TestClient(app)
    r = client.get("/api/constituency/KA-151")
    assert r.status_code == 200
    body = r.json()
    assert body["ac_name"] == "Bommanahalli"
    assert body["state"] == "KA"
    assert body["total_electors"] > 0


def test_constituency_unknown_returns_404() -> None:
    client = TestClient(app)
    r = client.get("/api/constituency/ZZ-999")
    assert r.status_code == 404
