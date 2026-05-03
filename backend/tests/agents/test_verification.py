"""VerificationAgent — 5 hermetic cases per AGENTS.md §10."""
from __future__ import annotations

from agents.verification import verification_agent
from tests.agents.conftest import tool_names
from tools.epic_search import (
    dedup_check,
    epic_search,
    parse_epic_ocr,
    suggest_corrections,
)


# 1. Happy path — Riya's EPIC returns one record from the demo dataset.
def test_epic_search_happy_path() -> None:
    r = epic_search(epic_number="ABC1234567")
    assert r["ok"] is True
    assert len(r["matches"]) == 1
    assert r["matches"][0]["name"] == "Riya Sharma"
    assert r["matches"][0]["is_synthetic"] is True


# 2. Edge — name+DOB returns the seeded duplicate pair (Anjali Verma).
def test_dedup_check_surfaces_pair() -> None:
    r = dedup_check(name="Anjali Verma", dob="1990-06-15")
    assert r["ok"] is True
    assert r["count"] == 2
    acs = {d["ac_code"] for d in r["duplicates"]}
    assert acs == {"UP-173", "UP-174"}


# 3. Language — prompt explicitly says respond in {language_code}.
def test_language_placeholder_present() -> None:
    assert "{language_code}" in verification_agent.instruction


# 4. Guardrail — prompt forbids speculation, cross-voter leakage, mock-data
#    over-promising.
def test_verification_guardrails_present() -> None:
    p = verification_agent.instruction.lower()
    assert "based on the demo dataset" in p
    assert "another voter" in p
    assert "form 7" in p


# 5. Tool failure — invalid EPIC raises envelope error not Python exception.
def test_invalid_epic_returns_error_envelope() -> None:
    r = epic_search(epic_number="not-an-epic-number")
    assert r["ok"] is False
    assert r["error"] == "invalid_epic_format"
    assert "user_message" in r


# bonus: OCR parsing extracts EPIC from noisy text.
def test_ocr_parse_extracts_epic() -> None:
    r = parse_epic_ocr("ELECTION COMM. INDIA EPIC No: ABC1234567 Riya")
    assert r["epic_number"] == "ABC1234567"
    assert r["confidence"] >= 0.8


# structural — required tools per AGENTS.md §3.
def test_verification_has_required_tools() -> None:
    required = {"epic_search", "dedup_check", "suggest_corrections", "parse_epic_ocr"}
    assert required.issubset(tool_names(verification_agent))


# suggest_corrections returns empty for unknown EPIC (graceful).
def test_suggest_corrections_unknown_epic_empty() -> None:
    r = suggest_corrections("ZZZ9999999")
    assert r["ok"] is True
    assert r["corrections"] == []
