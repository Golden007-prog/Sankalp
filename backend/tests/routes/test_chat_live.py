"""Live SSE end-to-end via FastAPI TestClient — hits real Vertex AI.

Opt-in: `pytest -m live`. Asserts the full SSE stage contract against
the real orchestrator + Gemini 2.5 Flash.
"""
from __future__ import annotations

import json
import os

import pytest
from fastapi.testclient import TestClient

from main import app
from sse import bridge

pytestmark = pytest.mark.live


def _need_vertex_env() -> None:
    if os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "").lower() != "true":
        pytest.skip("GOOGLE_GENAI_USE_VERTEXAI=true required for live test")
    if not os.environ.get("GOOGLE_CLOUD_PROJECT"):
        pytest.skip("GOOGLE_CLOUD_PROJECT required for live test")


def test_live_chat_streams_full_stage_sequence() -> None:
    """Real orchestrator + Vertex AI. Verifies the SSE contract end-to-end."""
    _need_vertex_env()
    bridge.reset_runner_factory()  # ensure no leftover fake from hermetic tests

    client = TestClient(app)
    body = {
        "message": "Please verify my voter record. My EPIC number is ABC1234567.",
    }
    with client.stream("POST", "/api/chat", json=body) as r:
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        assert "x-sankalp-session-id" in {k.lower() for k in r.headers.keys()}

        text = ""
        for chunk in r.iter_raw():
            text += chunk.decode("utf-8")

    events_seen = {
        line[len("event: "):]
        for line in text.splitlines()
        if line.startswith("event: ")
    }
    print(f"\n  events seen: {sorted(events_seen)}")

    # Core stage contract.
    assert "lang_detect" in events_seen
    assert "routing" in events_seen
    assert "final" in events_seen
    # At least one specialist or tool fired.
    assert any(e.startswith("specialist:") for e in events_seen) or "tool_call" in events_seen, (
        f"no specialist or tool_call event: {events_seen}"
    )

    # Final must be ok=true.
    data_lines = [
        line[len("data: "):]
        for line in text.splitlines()
        if line.startswith("data: ")
    ]
    final_data = None
    for ev_line, data_line in zip(
        [l[len("event: "):] for l in text.splitlines() if l.startswith("event: ")],
        data_lines,
    ):
        if ev_line == "final":
            final_data = json.loads(data_line)
            break
    assert final_data is not None
    assert final_data["ok"] is True
    assert final_data["text"]
    assert final_data["cost"]["tokens_in"] > 0
    print(f"  cost: in={final_data['cost']['tokens_in']} out={final_data['cost']['tokens_out']} ms={final_data['cost']['latency_ms']}")
