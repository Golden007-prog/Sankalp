"""EPIC search + voter-record helpers wrapping the data source.

Used by VerificationAgent (AGENTS.md §3) and BoothAgent (§4).
"""
from __future__ import annotations

import re
from datetime import date
from typing import Optional

from tools._envelope import err, ok
from tools.data_source import get_data_source

EPIC_RE = re.compile(r"^[A-Z]{3}\d{7}$")


def epic_search(
    epic_number: Optional[str] = None,
    name: Optional[str] = None,
    dob: Optional[str] = None,
    ac_code: Optional[str] = None,  # noqa: ARG001 (reserved for future filtering)
) -> dict:
    """Look up voters by EPIC OR (name [+ optional DOB])."""
    src = get_data_source()
    if epic_number:
        if not EPIC_RE.match(epic_number):
            return err(
                "invalid_epic_format",
                "That EPIC number doesn't look right — it should be 3 letters followed by 7 digits, like ABC1234567.",
            )
        rec = src.search_by_epic(epic_number)
        if rec is None:
            return ok(matches=[], note="not_found_in_demo_dataset")
        return ok(matches=[_record_to_dict(rec)])
    if name:
        dob_dt = date.fromisoformat(dob) if dob else None
        records = src.search_by_name_dob(name, dob_dt)
        return ok(
            matches=[_record_to_dict(r) for r in records],
            note="fuzzy_name_match" if dob is None else "name_dob_match",
        )
    return err("missing_query", "Please give me either an EPIC number, or a name and date of birth.")


def dedup_check(name: str, dob: str, ac_code: Optional[str] = None) -> dict:
    """Surface duplicate registrations across constituencies."""
    src = get_data_source()
    try:
        dob_dt = date.fromisoformat(dob)
    except ValueError:
        return err("invalid_dob_format", "Please give the date of birth as YYYY-MM-DD.")
    records = src.search_by_name_dob(name, dob_dt)
    if ac_code:
        records = [r for r in records if r.ac_code != ac_code]
    return ok(
        duplicates=[_record_to_dict(r) for r in records],
        count=len(records),
    )


def suggest_corrections(epic_number: str) -> dict:
    """Diff a record against canonical formats; returns suggestion list.

    For the hackathon dataset the only canonical issues we surface are
    incomplete address and missing relation_name; richer rules can land
    when real ECI data is wired up.
    """
    src = get_data_source()
    if not EPIC_RE.match(epic_number):
        return err("invalid_epic_format", "That EPIC number doesn't look right.")
    rec = src.search_by_epic(epic_number)
    if rec is None:
        return ok(corrections=[])
    suggestions = []
    if not rec.address.house or rec.address.house.strip() == "":
        suggestions.append({"field": "address.house", "issue": "missing_house_number"})
    if not rec.relation_name:
        suggestions.append({"field": "relation_name", "issue": "missing"})
    return ok(corrections=suggestions)


def parse_epic_ocr(raw_text: str) -> dict:
    """Extract an EPIC number from noisy OCR output via regex.
    Returns the first valid format match; consumers do the lookup."""
    if not raw_text:
        return err("empty_ocr", "I couldn't read anything from the photo. Please try again with better lighting.")
    m = re.search(r"\b([A-Z]{3}[0-9]{7})\b", raw_text.upper())
    if not m:
        return ok(epic_number=None, confidence=0.0, note="no_epic_format_match")
    return ok(epic_number=m.group(1), confidence=0.85)


def lookup_booth_by_epic(epic_number: str) -> dict:
    """BoothAgent's primary path."""
    src = get_data_source()
    if not EPIC_RE.match(epic_number):
        return err("invalid_epic_format", "That EPIC number doesn't look right.")
    booth = src.lookup_booth_by_voter(epic_number)
    if booth is None:
        return ok(booth=None, note="not_found_in_demo_dataset")
    return ok(booth=_booth_to_dict(booth))


def lookup_booth_by_pin(pincode: str, address: Optional[str] = None) -> dict:  # noqa: ARG001
    """Fallback path: pick the first booth in the AC mapped from this PIN."""
    src = get_data_source()
    ac_code = src.pin_to_ac(pincode)
    if ac_code is None:
        return ok(booth=None, note="pin_outside_demo_dataset")
    candidates = src.ac_to_booths.get(ac_code, []) if hasattr(src, "ac_to_booths") else []
    if not candidates:
        return ok(booth=None, note="no_booths_for_ac")
    booth = src.lookup_booth_by_id(candidates[0])
    if booth is None:
        return ok(booth=None, note="booth_index_inconsistent")
    return ok(booth=_booth_to_dict(booth), disclosure="based_on_pin_not_epic")


def get_accessibility(booth_id: str) -> dict:
    src = get_data_source()
    booth = src.lookup_booth_by_id(booth_id)
    if booth is None:
        return err("unknown_booth", "I couldn't find that booth in the demo dataset.")
    a = booth.accessibility
    return ok(
        wheelchair=a.wheelchair, ramp=a.ramp, ground_floor=a.ground_floor,
        sign_language=a.sign_language, braille_ballot=a.braille_ballot,
        language_assistance=list(a.language_assistance),
        synthetic=a.synthetic,
    )


def _record_to_dict(rec) -> dict:
    return {
        "epic_number": rec.epic_number,
        "name": rec.name,
        "name_native": rec.name_native,
        "dob": rec.dob.isoformat(),
        "gender": rec.gender,
        "ac_code": rec.ac_code,
        "booth_id": rec.booth_id,
        "address": {
            "house": rec.address.house, "street": rec.address.street,
            "locality": rec.address.locality, "city": rec.address.city,
            "state": rec.address.state, "pincode": rec.address.pincode,
        },
        "is_synthetic": rec.is_synthetic,
    }


def _booth_to_dict(b) -> dict:
    return {
        "booth_id": b.booth_id, "ac_code": b.ac_code,
        "name": b.name, "address": b.address,
        "lat": b.lat, "lng": b.lng,
        "voting_hours": b.voting_hours,
        "accessibility": {
            "wheelchair": b.accessibility.wheelchair,
            "ramp": b.accessibility.ramp,
            "ground_floor": b.accessibility.ground_floor,
            "language_assistance": list(b.accessibility.language_assistance),
            "sign_language": b.accessibility.sign_language,
            "braille_ballot": b.accessibility.braille_ballot,
            "synthetic": b.accessibility.synthetic,
        },
    }
