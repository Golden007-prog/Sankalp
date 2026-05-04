"""Story permalink route — uses a stubbed GCS module so tests are hermetic."""
from __future__ import annotations

import json
import sys
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from main import app


class _Blob:
    def __init__(self, exists: bool, payload: bytes = b"") -> None:
        self._exists = exists
        self._payload = payload

    def exists(self) -> bool:
        return self._exists

    def download_as_bytes(self) -> bytes:
        return self._payload


class _Bucket:
    def __init__(self, blobs: dict[str, _Blob]) -> None:
        self._blobs = blobs

    def blob(self, path: str) -> _Blob:
        return self._blobs.get(path, _Blob(exists=False))


class _Client:
    def __init__(self, blobs: dict[str, _Blob]) -> None:
        self._blobs = blobs

    def bucket(self, name: str) -> _Bucket:  # noqa: ARG002
        return _Bucket(self._blobs)


@pytest.fixture
def stub_gcs(monkeypatch):
    state: dict[str, dict[str, _Blob]] = {"blobs": {}}

    def _set_blobs(blobs: dict[str, _Blob]) -> None:
        state["blobs"] = blobs

    pkg = SimpleNamespace(Client=lambda **kw: _Client(state["blobs"]))
    monkeypatch.setitem(sys.modules, "google.cloud.storage", pkg)
    monkeypatch.setenv("STORAGE_BUCKET", "test-bucket")
    return _set_blobs


def test_story_route_happy_path(stub_gcs) -> None:
    payload = {
        "ac_code": "KA-151", "narrative": "Bommanahalli runs along Silk Board…",
        "cover_url": "/api/story/KA-151/cover.png", "permalink": "https://example/x",
    }
    stub_gcs({
        "story/KA-151.json": _Blob(exists=True, payload=json.dumps(payload).encode()),
    })
    client = TestClient(app)
    r = client.get("/api/story/KA-151")
    assert r.status_code == 200
    assert r.json()["ac_code"] == "KA-151"


def test_story_route_404_when_missing(stub_gcs) -> None:
    stub_gcs({})
    client = TestClient(app)
    r = client.get("/api/story/KA-151")
    assert r.status_code == 404


def test_story_invalid_ac_code(stub_gcs) -> None:
    stub_gcs({})
    client = TestClient(app)
    r = client.get("/api/story/foo")
    assert r.status_code == 400


def test_cover_route_streams_png(stub_gcs) -> None:
    stub_gcs({
        "story/KA-151/cover.png": _Blob(exists=True, payload=b"\x89PNG\r\n\x1a\nfake"),
    })
    client = TestClient(app)
    r = client.get("/api/story/KA-151/cover.png")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("image/png")
    assert b"PNG" in r.content
