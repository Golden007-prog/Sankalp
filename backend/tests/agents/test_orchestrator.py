"""OrchestratorAgent — 5 hermetic cases per AGENTS.md §10.

Structural + tool-behavior coverage. End-to-end LLM coverage is in
the live tests (`pytest -m live`).
"""
from __future__ import annotations

from agents.orchestrator import orchestrator
from tests.agents.conftest import tool_names
from tools.language import detect_language_rule


# 1. Happy path — orchestrator wires every tool AGENTS.md §1 requires.
def test_orchestrator_has_required_tools() -> None:
    names = tool_names(orchestrator)
    required = {
        "detect_language", "load_session", "update_session",
        "registration_agent", "verification_agent",
        "booth_agent", "story_agent",
    }
    assert required.issubset(names), f"missing: {required - names}"


# 2. Edge case — prompt is loaded verbatim from disk and matches docs.
def test_prompt_is_verbatim_from_agents_md() -> None:
    prompt = orchestrator.instruction
    # A handful of distinctive phrases that only this prompt contains.
    assert "You are Sankalp, a helpful guide for Indian voters." in prompt
    assert "{language_code}" in prompt
    assert "iCall helpline (9152987821)" in prompt


# 3. Language switch — rule-based detector handles the 7-language launch set.
def test_language_switch_detection() -> None:
    cases = [
        ("Hello, I want to register", "en"),
        ("नमस्ते मुझे रजिस्टर करना है", "hi"),
        ("ನಮಸ್ಕಾರ ನಾನು register ಮಾಡಬೇಕು", "kn"),
        ("வணக்கம் எனக்கு register வேண்டும்", "ta"),
        ("నాకు register కావాలి", "te"),
        ("আমি register করতে চাই", "bn"),
        ("मला नोंदणी करायची आहे सांगा", "mr"),
    ]
    for text, expected in cases:
        assert detect_language_rule(text) == expected, f"{text!r} → {detect_language_rule(text)}"


# 4. Guardrail — prompt forbids Aadhaar/passwords/political-opinion routing.
def test_orchestrator_guardrails_present() -> None:
    p = orchestrator.instruction.lower()
    assert "aadhaar" in p
    assert "candidate" in p
    assert "voters.eci.gov.in" in p


# 5. Tool failure — load_session degrades to in-memory when Firestore is
#    unreachable; orchestrator doesn't crash, returns valid envelope.
def test_load_session_graceful_degradation() -> None:
    from tools.session import _firestore_disabled  # noqa: PLC0415
    from tools.session import load_session, new_session_id

    # Force the in-memory path (mimics auth failure).
    import tools.session as ses_mod
    ses_mod._firestore_disabled = True
    try:
        sid = new_session_id()
        env = load_session(sid)
        assert env["ok"] is True
        assert env["state"]["session_id"] == sid
        assert env["state"]["language"] == "en"
    finally:
        ses_mod._firestore_disabled = bool(_firestore_disabled)
