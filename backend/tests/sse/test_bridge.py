"""Hermetic SSE bridge tests — fake ADK runner yields canned events,
bridge translates them to the SSE stage contract.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, List, Optional

import pytest

from sse import bridge


# ---------- Fake ADK shapes ----------

@dataclass
class _Part:
    text: Optional[str] = None
    function_call: Optional[Any] = None


@dataclass
class _FnCall:
    name: str


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
class _AdkSession:
    id: str = "fake-adk-session"


class _FakeSessionService:
    async def create_session(self, *, app_name: str, user_id: str, session_id: str | None = None, state: dict | None = None) -> _AdkSession:  # noqa: ARG002
        return _AdkSession(id=session_id or "fake-adk-session")


class _FakeRunner:
    def __init__(self, events: List[_Event]) -> None:
        self._events = events
        self.session_service = _FakeSessionService()

    async def run_async(self, *, user_id: str, session_id: str, new_message: Any) -> AsyncIterator[_Event]:  # noqa: ARG002
        for e in self._events:
            yield e


def _factory(events: List[_Event]):
    def _make() -> _FakeRunner:
        return _FakeRunner(events)
    return _make


@pytest.fixture(autouse=True)
def _reset_runner():
    yield
    bridge.reset_runner_factory()


# ---------- Tests ----------

@pytest.mark.asyncio
async def test_bridge_emits_stages_in_order() -> None:
    events = [
        # detect_language tool fires from orchestrator.
        _Event(
            author="orchestrator",
            content=_Content(parts=[_Part(function_call=_FnCall(name="detect_language"))]),
        ),
        # Sub-agent transitions to registration.
        _Event(
            author="registration_agent",
            content=_Content(parts=[_Part(text="Sure, I'll help you fill Form 6. ")]),
        ),
        _Event(
            author="registration_agent",
            content=_Content(parts=[_Part(text="What's your full name?")]),
            usage_metadata=_Usage(prompt_token_count=200, candidates_token_count=42),
            final=True,
        ),
    ]
    bridge.set_runner_factory(_factory(events))

    seen: list[tuple[str, dict]] = []
    async for ev in bridge.stream_chat(message="I want to register", session_id="sess_test_xyz12345"):
        seen.append((ev["event"], json.loads(ev["data"])))

    names = [name for name, _ in seen]
    assert names[0] == "lang_detect"
    assert names[1] == "routing"
    assert "specialist:registration_agent" in names
    assert "tool_call" in names
    assert "delta" in names
    assert names[-1] == "final"

    final = next(d for n, d in seen if n == "final")
    assert final["ok"] is True
    assert "Form 6" in final["text"]
    assert final["intent"] == "register"
    assert final["cost"]["tokens_in"] == 200
    assert final["cost"]["tokens_out"] == 42


@pytest.mark.asyncio
async def test_bridge_runner_failure_emits_final_with_error() -> None:
    class _BoomRunner:
        session_service = _FakeSessionService()

        async def run_async(self, **_kw: Any) -> AsyncIterator[_Event]:
            raise RuntimeError("vertex_oom")
            yield  # pragma: no cover  (makes this an async generator)

    bridge.set_runner_factory(lambda: _BoomRunner())

    seen: list[tuple[str, dict]] = []
    async for ev in bridge.stream_chat(message="hi", session_id="sess_boom_abcd1234"):
        seen.append((ev["event"], json.loads(ev["data"])))

    final = next(d for n, d in seen if n == "final")
    assert final["ok"] is False
    assert "vertex_oom" in final["error"]
    assert "user_message" in final


@pytest.mark.asyncio
async def test_bridge_parses_voter_record_marker() -> None:
    payload_text = (
        "Found you in the dataset. "
        '[VOTER_RECORD epic="ABC1234567" name="Riya Sharma" ac="KA-151" booth="KA-151_001"]'
    )
    events = [
        _Event(
            author="verification_agent",
            content=_Content(parts=[_Part(text=payload_text)]),
            usage_metadata=_Usage(prompt_token_count=300, candidates_token_count=80),
            final=True,
        ),
    ]
    bridge.set_runner_factory(_factory(events))

    final = None
    async for ev in bridge.stream_chat(message="check ABC1234567", session_id="sess_marker_test1234"):
        if ev["event"] == "final":
            final = json.loads(ev["data"])

    assert final is not None
    assert final["markers"]["voter_record"]["epic"] == "ABC1234567"
    assert final["intent"] == "verify"
