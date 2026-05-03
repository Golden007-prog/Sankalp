"""Phase 5 — bridge persists structured-marker state so the next turn's
RegistrationAgent can short-circuit Form 8 (skip re-asking for EPIC/AC).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, List, Optional

import pytest

from sse import bridge
from tools import session as session_mod


@dataclass
class _Part:
    text: Optional[str] = None
    function_call: Optional[Any] = None


@dataclass
class _Content:
    parts: List[_Part] = field(default_factory=list)


@dataclass
class _Event:
    author: str = "orchestrator"
    content: _Content = field(default_factory=_Content)
    usage_metadata: Optional[Any] = None
    final: bool = False

    def is_final_response(self) -> bool:
        return self.final


@dataclass
class _Sess:
    id: str = "fake"


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
def _reset_runner_and_session():
    yield
    bridge.reset_runner_factory()
    # in-memory session store reset between tests
    session_mod._inmem._data.clear()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_voter_record_marker_persists_to_session() -> None:
    payload_text = (
        "Found you in the dataset. "
        '[VOTER_RECORD epic="ABC1234567" name="Riya Sharma" ac="KA-151" booth="KA-151_001"]'
    )
    bridge.set_runner_factory(lambda: _FakeRunner([
        _Event(
            author="verification_agent",
            content=_Content(parts=[_Part(text=payload_text)]),
            final=True,
        ),
    ]))

    sid = "sess_phase5_state_xyz"
    async for _ in bridge.stream_chat(message="Verify ABC1234567", session_id=sid):
        pass

    loaded = session_mod.load_session(sid)
    assert loaded["ok"] is True
    state = loaded["state"]
    assert state["last_voter_record"]["epic_number"] == "ABC1234567"
    assert state["last_voter_record"]["ac_code"] == "KA-151"
    assert state["last_intent"] == "verify"


@pytest.mark.asyncio
async def test_no_marker_no_state_writes() -> None:
    """Plain reply without markers shouldn't pollute durable state."""
    bridge.set_runner_factory(lambda: _FakeRunner([
        _Event(
            author="orchestrator",
            content=_Content(parts=[_Part(text="Sure, what's your name?")]),
            final=True,
        ),
    ]))

    sid = "sess_phase5_no_marker_xyz"
    async for _ in bridge.stream_chat(message="hello", session_id=sid):
        pass

    state = session_mod.load_session(sid)["state"]
    assert state.get("last_voter_record") is None
    assert state.get("last_booth") is None
