"""Hermetic /api/vision/epic — patches detect_epic_text."""
from __future__ import annotations

from fastapi.testclient import TestClient

from main import app
from tools import ocr as ocr_mod


def test_vision_epic_returns_parsed(monkeypatch) -> None:
    def fake(_: bytes) -> dict:
        return {"ok": True, "epic_number": "ABC1234567", "raw_text": "EPIC ABC1234567", "confidence": 0.85, "degraded": False}
    monkeypatch.setattr(ocr_mod, "detect_epic_text", fake)
    # vision route imports at top-level, so re-route the module attribute too.
    from routes import vision as route_mod
    monkeypatch.setattr(route_mod, "detect_epic_text", fake)

    client = TestClient(app)
    files = {"file": ("epic.jpg", b"\xff\xd8\xff fake jpeg bytes", "image/jpeg")}
    r = client.post("/api/vision/epic", files=files)
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["epic_number"] == "ABC1234567"
    assert body["session_id"]


def test_vision_rejects_unsupported_content_type() -> None:
    client = TestClient(app)
    files = {"file": ("epic.txt", b"not an image", "text/plain")}
    r = client.post("/api/vision/epic", files=files)
    assert r.status_code == 415


def test_vision_rejects_empty() -> None:
    client = TestClient(app)
    files = {"file": ("epic.jpg", b"", "image/jpeg")}
    r = client.post("/api/vision/epic", files=files)
    assert r.status_code == 400
