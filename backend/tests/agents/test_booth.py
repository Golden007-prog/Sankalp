"""BoothAgent — 5 hermetic cases per AGENTS.md §10."""
from __future__ import annotations

from agents.booth import booth_agent
from tests.agents.conftest import tool_names
from tools.epic_search import (
    get_accessibility,
    lookup_booth_by_epic,
    lookup_booth_by_pin,
)
from tools.maps import get_directions


# 1. Happy — Riya's EPIC resolves to her booth.
def test_lookup_booth_by_epic_happy() -> None:
    r = lookup_booth_by_epic("ABC1234567")
    assert r["ok"] is True
    assert r["booth"]["booth_id"] == "KA-151_001"
    assert r["booth"]["accessibility"]["synthetic"] is True


# 2. Edge — PIN-only lookup falls back to first booth in the AC, with
#    a disclosure flag flipped on for the prompt to surface.
def test_lookup_booth_by_pin_disclosure() -> None:
    r = lookup_booth_by_pin("560068")
    assert r["ok"] is True
    assert r["booth"] is not None
    assert r.get("disclosure") == "based_on_pin_not_epic"


# 3. Language — prompt mandates response in {language_code}.
def test_booth_prompt_localised() -> None:
    assert "{language_code}" in booth_agent.instruction
    assert "BOOTH_CARD" in booth_agent.instruction


# 4. Guardrail — prompt requires PIN-only disclosure + flags >2km warning.
def test_booth_guardrails_present() -> None:
    p = booth_agent.instruction.lower()
    assert "based on your address" in p
    assert "verify epic" in p
    assert "2 km" in p
    assert "other voters' assignments" in p


# 5. Tool failure — without GOOGLE_MAPS_API_KEY, get_directions returns
#    a degraded envelope with a deeplink instead of crashing.
def test_directions_graceful_degradation() -> None:
    r = get_directions("Bommanahalli", "Government Higher Primary School")
    assert r["ok"] is True
    assert r["degraded"] is True
    assert r["deeplink"].startswith("https://www.google.com/maps/dir/")


# bonus: get_accessibility for a real booth.
def test_get_accessibility() -> None:
    r = get_accessibility("KA-151_001")
    assert r["ok"] is True
    assert r["synthetic"] is True
    assert isinstance(r["language_assistance"], list)


# structural — required tools per AGENTS.md §4.
def test_booth_has_required_tools() -> None:
    required = {"lookup_booth_by_epic", "lookup_booth_by_pin",
                "get_directions", "get_accessibility", "nearest_landmarks"}
    assert required.issubset(tool_names(booth_agent))
