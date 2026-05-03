"""StoryAgent — 5 hermetic cases per AGENTS.md §10."""
from __future__ import annotations

from agents.story import story_agent
from tests.agents.conftest import tool_names
from tools.constituency import (
    get_constituency,
    get_turnout_history,
    get_win_margin_history,
)
from tools.imagen import imagen_cover
from tools.story_store import store_story


# 1. Happy path — KA-151 returns rich constituency facts the agent needs.
def test_get_constituency_happy() -> None:
    r = get_constituency("KA-151")
    assert r["ok"] is True
    assert r["ac_name"] == "Bommanahalli"
    assert r["total_electors"] > 0
    assert "BTM Layout" in r["key_landmarks"]


# 2. Edge — get_history returns 5 elections with the smallest margin
#    available for the StoryAgent's "closeness moment" beat.
def test_smallest_margin_available() -> None:
    margins = get_win_margin_history("KA-151")["records"]
    assert len(margins) == 5
    smallest = min(m["win_margin"] for m in margins)
    assert smallest > 0
    # Bommanahalli's smallest seeded margin is 4218 (anchor data).
    assert smallest == 4218


# 3. Language — prompt mandates response in {language_code}.
def test_story_language_placeholder_present() -> None:
    assert "{language_code}" in story_agent.instruction
    assert "STORY ac_code=" in story_agent.instruction


# 4. Guardrail — Imagen refuses political/religious prompts; prompt forbids
#    naming candidates or parties.
def test_story_guardrails_present() -> None:
    p = story_agent.instruction.lower()
    assert "do not name candidates" in p
    assert "do not name parties" in p
    assert "no political symbols" in p

    bad = imagen_cover("a political party rally with flags")
    assert bad["ok"] is False
    assert bad["error"] == "forbidden_prompt"


# 5. Tool failure — get_turnout_history on unknown AC degrades cleanly.
def test_unknown_ac_history_graceful() -> None:
    r = get_turnout_history("ZZ-999")
    assert r["ok"] is False
    assert "user_message" in r


# bonus: store_story persists locally with a permalink.
def test_store_story_local() -> None:
    r = store_story("session_phase2_test_xyz", "KA-151", "Test narrative for Bommanahalli.")
    assert r["ok"] is True
    assert r["permalink"]


# structural — required tools per AGENTS.md §5.
def test_story_has_required_tools() -> None:
    required = {"get_constituency", "get_turnout_history", "get_win_margin_history",
                "imagen_cover", "tts_narrate", "store_story"}
    assert required.issubset(tool_names(story_agent))


# StoryAgent uses Pro per CLAUDE.md "Stack" rule 4.
def test_story_uses_pro_model() -> None:
    assert "pro" in story_agent.model.lower()
