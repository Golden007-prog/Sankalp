"""RegistrationAgent — 5 hermetic cases per AGENTS.md §10."""
from __future__ import annotations

from pathlib import Path

from agents.registration import registration_agent
from tests.agents.conftest import tool_names
from tools.constituency import pin_to_constituency, validate_field
from tools.form_pdf import generate_form6_pdf, generate_form8_pdf


# 1. Happy path — slot fill ends with a Form 6 PDF for Riya's profile.
def test_form6_pdf_happy_path() -> None:
    state = {
        "full_name": "Riya Sharma", "full_name_native": "रिया शर्मा",
        "dob": "12/04/2007", "gender": "F",
        "relation_type": "father", "relation_name": "Rajesh Sharma",
        "house": "42", "street": "MG Road", "locality": "Bommanahalli",
        "city": "Bengaluru", "state": "Karnataka", "pincode": "560068",
        "ac_code": "KA-151", "ac_name": "Bommanahalli", "mobile": "9999999999",
    }
    r = generate_form6_pdf("session_riya_demo_001", state)
    assert r["ok"] is True
    assert r["form_type"] == "6"
    assert Path(r["url"].replace("file:///", "")).exists() or r["storage"] == "cloud"


# 2. Edge — DOB format validation rejects ISO and accepts DD/MM/YYYY.
def test_validate_field_dob_format() -> None:
    assert validate_field("dob", "2007-04-12")["valid"] is False
    assert validate_field("dob", "12/04/2007")["valid"] is True
    assert validate_field("pincode", "1234")["valid"] is False
    assert validate_field("pincode", "560068")["valid"] is True


# 3. Language — agent prompt explicitly localises field examples.
def test_prompt_localises_field_examples() -> None:
    p = registration_agent.instruction
    assert "{language_code}" in p
    assert "DD/MM/YYYY" in p
    assert "PDF_READY" in p  # marker for frontend


# 4. Guardrail — prompt refuses Aadhaar / OTP / submit-to-ECI claims.
def test_registration_guardrails_present() -> None:
    p = registration_agent.instruction.lower()
    assert "aadhaar" in p
    assert "auto-submit" in p
    assert "otp" in p
    assert "voters.eci.gov.in" in p


# 5. Tool failure — generate_form8_pdf rejects invalid change_type.
def test_form8_invalid_change_type() -> None:
    r = generate_form8_pdf("session_xxxxxxxxx", {"epic_number": "ABC1234567"}, "weird")
    assert r["ok"] is False
    assert "user_message" in r


# bonus structural: required tools all present.
def test_registration_has_required_tools() -> None:
    required = {"validate_field", "pin_to_constituency",
                "generate_form6_pdf", "generate_form8_pdf",
                "update_form_state"}
    assert required.issubset(tool_names(registration_agent))


# pin lookup smoke
def test_pin_to_constituency_round_trip() -> None:
    r = pin_to_constituency("560068")
    assert r["ok"] is True
    assert r["ac_code"] == "KA-151"
