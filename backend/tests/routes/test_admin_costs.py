"""Admin costs endpoint — hermetic via stubbed firestore."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from main import app


class _Doc:
    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def to_dict(self) -> dict[str, Any]:
        return self._data


class _Query:
    def __init__(self, docs: list[_Doc]) -> None:
        self._docs = docs

    def where(self, *args: Any, **kw: Any) -> "_Query":  # noqa: ARG002
        return self

    def stream(self):
        return iter(self._docs)


class _Collection:
    def __init__(self, docs: list[_Doc]) -> None:
        self._docs = docs

    def where(self, *args: Any, **kw: Any) -> _Query:
        return _Query(self._docs)


class _FsClient:
    def __init__(self, docs: list[_Doc]) -> None:
        self._docs = docs

    def collection(self, name: str) -> _Collection:  # noqa: ARG002
        return _Collection(self._docs)


@pytest.fixture
def stub_firestore(monkeypatch):
    state: dict[str, list[_Doc]] = {"docs": []}

    def _set(docs: list[dict[str, Any]]) -> None:
        state["docs"] = [_Doc(d) for d in docs]

    pkg = SimpleNamespace(Client=lambda **kw: _FsClient(state["docs"]))
    monkeypatch.setitem(sys.modules, "google.cloud.firestore", pkg)
    monkeypatch.setenv("SANKALP_ADMIN_KEY", "secret123")
    return _set


def test_admin_requires_key(stub_firestore) -> None:
    stub_firestore([])
    client = TestClient(app)
    r = client.get("/api/admin/costs")
    assert r.status_code == 422  # FastAPI rejects missing query param


def test_admin_rejects_bad_key(stub_firestore) -> None:
    stub_firestore([])
    client = TestClient(app)
    r = client.get("/api/admin/costs?key=wrong")
    assert r.status_code == 403


def test_admin_aggregates_costs(stub_firestore) -> None:
    now = datetime.now(timezone.utc)
    stub_firestore([
        {"session_id": "s1", "agent": "orchestrator", "model": "gemini-2.5-flash",
         "tokens_in": 100, "tokens_out": 30, "latency_ms": 500, "created_at": now},
        {"session_id": "s2", "agent": "orchestrator", "model": "gemini-2.5-flash",
         "tokens_in": 150, "tokens_out": 40, "latency_ms": 1500, "created_at": now},
        {"session_id": "s2", "agent": "story_agent", "model": "gemini-2.5-pro",
         "tokens_in": 2000, "tokens_out": 250, "latency_ms": 21000, "created_at": now},
    ])
    client = TestClient(app)
    r = client.get("/api/admin/costs?key=secret123")
    assert r.status_code == 200
    body = r.json()
    assert body["request_count"] == 3
    assert body["session_count"] == 2
    assert body["total_tokens_in"] == 2250
    assert body["by_agent"]["orchestrator"]["requests"] == 2
    assert body["by_model"]["gemini-2.5-pro"]["tokens_out"] == 250
    assert body["latency_ms"]["max"] >= 21000


def test_admin_empty_returns_zeros(stub_firestore) -> None:
    stub_firestore([])
    client = TestClient(app)
    r = client.get("/api/admin/costs?key=secret123")
    assert r.status_code == 200
    body = r.json()
    assert body["request_count"] == 0
    assert body["latency_ms"]["p50"] == 0
