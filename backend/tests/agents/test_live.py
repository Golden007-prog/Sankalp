"""Live integration tests — hit real Vertex AI / Gemini.

Opt in via `pytest -m live`. Skipped by default. Budget: ~$0.10 of the
$1.00 Phase 2 budget (Phase prompt §3 in claude-code.md).

Required env (or ADC):
  GOOGLE_GENAI_USE_VERTEXAI=true
  GOOGLE_CLOUD_PROJECT=sankalp-495216
  GOOGLE_CLOUD_LOCATION=asia-south1   (or us-central1)
  GOOGLE_APPLICATION_CREDENTIALS=path/to/sa-key.json   (or `gcloud auth application-default login`)
"""
from __future__ import annotations

import os
from typing import Any

import pytest
from google.adk.runners import InMemoryRunner
from google.genai import types as genai_types

from agents.orchestrator import orchestrator
from agents.story import story_agent

pytestmark = pytest.mark.live


def _need_vertex_env() -> None:
    if os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "").lower() != "true":
        pytest.skip("GOOGLE_GENAI_USE_VERTEXAI=true required for live test")
    if not os.environ.get("GOOGLE_CLOUD_PROJECT"):
        pytest.skip("GOOGLE_CLOUD_PROJECT required for live test")


async def _drain(runner: InMemoryRunner, session_id: str, user_id: str, text: str) -> dict[str, Any]:
    """Run the agent and collect: final text, tool-call trace, token usage."""
    final_text = ""
    tool_calls: list[str] = []
    tokens_in = tokens_out = 0
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=genai_types.Content(role="user", parts=[genai_types.Part(text=text)]),
    ):
        # Tool calls live in event.content.parts when ADK invokes a tool.
        content = getattr(event, "content", None)
        if content and getattr(content, "parts", None):
            for p in content.parts:
                fc = getattr(p, "function_call", None)
                if fc and getattr(fc, "name", None):
                    tool_calls.append(fc.name)
                if getattr(p, "text", None) and getattr(event, "is_final_response", lambda: False)():
                    final_text += p.text
        usage = getattr(event, "usage_metadata", None)
        if usage is not None:
            tokens_in += getattr(usage, "prompt_token_count", 0) or 0
            tokens_out += getattr(usage, "candidates_token_count", 0) or 0
    return {"text": final_text, "tool_calls": tool_calls, "tokens_in": tokens_in, "tokens_out": tokens_out}


# Live test 1 — Orchestrator routes register intent to RegistrationAgent.
async def test_live_orchestrator_routes_register() -> None:
    _need_vertex_env()
    runner = InMemoryRunner(agent=orchestrator, app_name="sankalp")
    sess = await runner.session_service.create_session(
        app_name="sankalp", user_id="phase2_live_user",
        state={"language_code": "en"},
    )
    result = await _drain(runner, sess.id, sess.user_id, "I want to register to vote.")
    assert result["text"], f"orchestrator returned empty text; tool_calls={result['tool_calls']}"
    # Either it routed to the RegistrationAgent OR it asked a clarifying
    # question that mentions Form 6 / registration. Both satisfy AGENTS.md §1.
    routed = "registration_agent" in result["tool_calls"]
    mentions_register = "registration" in result["text"].lower() or "form 6" in result["text"].lower() or "form6" in result["text"].lower()
    assert routed or mentions_register, (
        f"neither routed nor mentioned registration. trace={result['tool_calls']!r} "
        f"text={result['text']!r}"
    )
    print(f"\n  tokens in/out: {result['tokens_in']}/{result['tokens_out']}")
    print(f"  trace: {result['tool_calls']}")


# Live test 2 — StoryAgent generates a 150+ word narrative for KA-151.
async def test_live_story_agent_bommanahalli() -> None:
    _need_vertex_env()
    runner = InMemoryRunner(agent=story_agent, app_name="sankalp")
    sess = await runner.session_service.create_session(
        app_name="sankalp", user_id="phase2_live_user",
        state={"language_code": "en"},
    )
    result = await _drain(
        runner, sess.id, sess.user_id,
        "Write the civic story for AC code KA-151. Respond in English. {language_code}=en"
    )
    text = result["text"]
    word_count = len(text.split())
    assert word_count >= 150, f"narrative only {word_count} words; want ≥150. text={text!r}"
    assert "Bommanahalli" in text, f"narrative missing constituency name. text={text!r}"
    # Must cite at least one real margin number from the dataset
    # (anchor margins for KA-151: 4218, 5811, 8453, 12011, 23218).
    margins = ("4218", "5811", "8453", "12011", "23218",
               "4,218", "5,811", "8,453", "12,011", "23,218")
    assert any(m in text for m in margins), f"narrative missing real margin. text={text!r}"
    print(f"\n  words: {word_count}, tokens in/out: {result['tokens_in']}/{result['tokens_out']}")
