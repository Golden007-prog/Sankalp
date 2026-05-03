"""Hermetic /api/chat: TestClient streams SSE with a fake ADK runner."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, List, Optional

import pytest
from fastapi.testclient import TestClient

from main import app
from sse import bridge


@dataclass
class _Part:
    text: Optional[str] = None
    function_call: Optional[Any] = None


@dataclass
class _Content:
    parts: List[_Part] = field(default_factory=list)


@dataclass
class _Usage:
    prompt_token_count: int = 0
    candidates_token_count: int = 0


@dataclass
class _Event:
    author: str = "orchestrator"
    content: _Content = field(default_factory=_Content)
    usage_metadata: Optional[_Usage] = None
    final: bool = False

    def is_final_response(self) -> bool:
        return self.final


@dataclass
class _Sess:
    id: str


class _SessionSvc:
    async def create_session(self, **kw: Any) -> _Sess:
        return _Sess(id=kw.get("session_id") or "fake")


class _FakeRunner:
    def __init__(self, events: List[_Event]) -> None:
        self._events = events
        self.session_service = _SessionSvc()

    async def run_async(self, **_kw: Any) -> AsyncIterator[_Event]:
        for e in self._events:
            yield e


@pytest.fixture(autouse=True)
def _reset():
    yield
    bridge.reset_runner_factory()


def _set_canned_runner() -> None:
    canned = [
        _Event(author="registration_agent",
               content=_Content(parts=[_Part(text="Sure, ")])),
        _Event(author="registration_agent",
               content=_Content(parts=[_Part(text="what is your full name?")]),
               usage_metadata=_Usage(prompt_token_count=180, candidates_token_count=24),
               final=True),
    ]
    bridge.set_runner_factory(lambda: _FakeRunner(canned))


def test_chat_streams_four_stages_and_session_header() -> None:
    _set_canned_runner()
    client = TestClient(app)
    body = {"message": "I want to register to vote"}
    with client.stream("POST", "/api/chat", json=body) as r:
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        sid_header = r.headers.get("x-sankalp-session-id")
        assert sid_header and len(sid_header) >= 8

        text = ""
        for chunk in r.iter_raw():
            text += chunk.decode("utf-8")

    events = [line[len("event: "):] for line in text.splitlines() if line.startswith("event: ")]
    assert "lang_detect" in events
    assert "routing" in events
    assert any(e.startswith("specialist:") for e in events), events
    assert "delta" in events
    assert "final" in events

    # Final payload contains text + cost summary.
    data_lines = [line[len("data: "):] for line in text.splitlines() if line.startswith("data: ")]
    parsed_final = next(
        json.loads(d) for line, d in zip(events, data_lines) if line == "final"
    )
    assert parsed_final["ok"] is True
    assert "full name" in parsed_final["text"].lower()
    assert parsed_final["cost"]["tokens_in"] == 180


def test_chat_validates_input() -> None:
    client = TestClient(app)
    r = client.post("/api/chat", json={"message": ""})
    assert r.status_code == 422  # pydantic min_length
