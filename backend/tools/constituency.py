"""StoryAgent's constituency-data tools.

Thin wrappers around MockElectoralDataSource — the StoryAgent calls
these to gather facts before composing its narrative. See AGENTS.md §5.
"""
from __future__ import annotations

from typing import Optional

from tools._envelope import err, ok
from tools.data_source import get_data_source


def get_constituency(ac_code: str) -> dict:
    src = get_data_source()
    c = src.get_constituency(ac_code)
    if c is None:
        return err(
            "unknown_ac_code",
            "I don't have data for that constituency in the demo dataset (covers 100 ACs).",
        )
    return ok(
        ac_code=c.ac_code, ac_name=c.ac_name, ac_name_native=c.ac_name_native,
        state=c.state, state_name=c.state_name, district=c.district,
        lok_sabha_code=c.lok_sabha_code, lok_sabha_name=c.lok_sabha_name,
        type=c.type,
        total_electors=c.total_electors,
        male_electors=c.male_electors, female_electors=c.female_electors,
        third_gender_electors=c.third_gender_electors,
        total_booths=c.total_booths,
        centroid={"lat": c.centroid_lat, "lng": c.centroid_lng},
        demographics={
            "literacy_pct": c.demographics.literacy_pct,
            "urban_pct": c.demographics.urban_pct,
            "primary_languages": list(c.demographics.primary_languages),
            "is_synthetic": c.demographics.is_synthetic,
        },
        key_landmarks=list(c.key_landmarks),
        provenance={
            "name_and_codes": c.provenance.name_and_codes,
            "elections": c.provenance.elections,
            "demographics": c.provenance.demographics,
            "booths": c.provenance.booths,
            "notes": c.provenance.notes,
        },
    )


def get_turnout_history(ac_code: str) -> dict:
    src = get_data_source()
    c = src.get_constituency(ac_code)
    if c is None:
        return err("unknown_ac_code", "No data for that constituency in the demo dataset.")
    return ok(
        records=[
            {
                "year": e.year,
                "type": e.type,
                "turnout_pct": e.turnout_pct,
                "total_votes_polled": e.total_votes_polled,
                "is_synthetic_election": e.is_synthetic_election,
                "source": e.source,
            }
            for e in c.elections
        ]
    )


def get_win_margin_history(ac_code: str) -> dict:
    src = get_data_source()
    c = src.get_constituency(ac_code)
    if c is None:
        return err("unknown_ac_code", "No data for that constituency in the demo dataset.")
    return ok(
        records=[
            {
                "year": e.year,
                "type": e.type,
                "winner_party": e.winner_party,
                "runner_up_party": e.runner_up_party,
                "win_margin": e.win_margin,
                "is_synthetic_election": e.is_synthetic_election,
                "source": e.source,
            }
            for e in c.elections
        ]
    )


def pin_to_constituency(pincode: str) -> dict:
    src = get_data_source()
    try:
        ac_code = src.pin_to_ac(pincode)
    except ValueError as e:
        return err(f"invalid_pin: {e}", "Please give a 6-digit Indian PIN code.")
    if ac_code is None:
        return ok(ac_code=None, note="pin_outside_demo_dataset")
    c = src.get_constituency(ac_code)
    if c is None:
        return ok(ac_code=ac_code)
    return ok(
        ac_code=ac_code, ac_name=c.ac_name, state=c.state,
        state_name=c.state_name, district=c.district,
    )


def validate_field(field_name: str, value: str, language: Optional[str] = None) -> dict:  # noqa: ARG001
    """Format-validate a Form 6/8 field. Lightweight regex/length checks —
    semantic validation (DOB ≥ 18, Pin ⇒ AC) lives in the agent prompt.
    """
    if not value or not value.strip():
        return ok(valid=False, error_message="This field can't be empty.")
    v = value.strip()
    if field_name == "dob":
        import re as _re  # local
        if not _re.match(r"^(\d{2})/(\d{2})/(\d{4})$", v):
            return ok(valid=False, error_message="Use DD/MM/YYYY, like 12/04/2007.")
    elif field_name == "pincode":
        if not v.isdigit() or len(v) != 6:
            return ok(valid=False, error_message="PIN code is 6 digits.")
    elif field_name == "mobile":
        digits = "".join(c for c in v if c.isdigit())
        if len(digits) not in (10, 12):
            return ok(valid=False, error_message="Indian mobile numbers are 10 digits, optionally with +91 prefix.")
    elif field_name == "email":
        if "@" not in v or "." not in v.split("@")[-1]:
            return ok(valid=False, error_message="That doesn't look like a valid email.")
    elif field_name == "epic_number":
        import re as _re
        if not _re.match(r"^[A-Z]{3}\d{7}$", v.upper()):
            return ok(valid=False, error_message="EPIC numbers are 3 letters + 7 digits, like ABC1234567.")
    return ok(valid=True)
