from __future__ import annotations

from datetime import date

import pytest

from schemas.electoral import AccessibilityFlags, VoterRecord
from tools.electoral_data import MockElectoralDataSource


@pytest.fixture(scope="module")
def src() -> MockElectoralDataSource:
    return MockElectoralDataSource()


# 1. Happy path — known persona round-trips through epic search.
def test_search_by_epic_happy_path(src: MockElectoralDataSource) -> None:
    riya = src.search_by_epic("ABC1234567")
    assert riya is not None
    assert riya.name == "Riya Sharma"
    assert riya.ac_code == "KA-151"
    assert riya.dob == date(2007, 4, 12)


# 2. Invalid EPIC format raises ValueError (per ECI's 3-letter + 7-digit rule).
def test_search_by_epic_invalid_format(src: MockElectoralDataSource) -> None:
    with pytest.raises(ValueError):
        src.search_by_epic("not-an-epic")
    with pytest.raises(ValueError):
        src.search_by_epic("ABC123")  # too short


# 3. Unknown EPIC returns None (graceful, per VerificationAgent prompt).
def test_search_by_epic_unknown_returns_none(src: MockElectoralDataSource) -> None:
    assert src.search_by_epic("ZZZ9999999") is None


# 4. Name+DOB fuzzy returns ≥1 record for the seeded persona.
def test_search_by_name_dob_happy(src: MockElectoralDataSource) -> None:
    matches = src.search_by_name_dob("Priya Reddy", date(1996, 3, 21))
    assert len(matches) >= 1
    assert any(m.epic_number == "TGS9912204" for m in matches)


# 5. Duplicate-registration scenario — same name + DOB across two ACs
#    surfaces 2 records, exercising VerificationAgent's dedup_check path.
def test_search_by_name_dob_duplicate(src: MockElectoralDataSource) -> None:
    dups = src.search_by_name_dob("Anjali Verma", date(1990, 6, 15))
    assert len(dups) == 2
    assert {v.ac_code for v in dups} == {"UP-173", "UP-174"}


# 6. Booth lookup by id round-trips and accessibility is always synthetic.
def test_lookup_booth_by_id_happy(src: MockElectoralDataSource) -> None:
    booth = src.lookup_booth_by_id("KA-151_001")
    assert booth is not None
    assert booth.ac_code == "KA-151"
    assert isinstance(booth.accessibility, AccessibilityFlags)
    assert booth.accessibility.synthetic is True


# 7. Voter-to-booth resolves through the EPIC index.
def test_lookup_booth_by_voter(src: MockElectoralDataSource) -> None:
    booth = src.lookup_booth_by_voter("ABC1234567")
    assert booth is not None
    assert booth.booth_id == "KA-151_001"


# 8. get_constituency happy + unknown.
def test_get_constituency(src: MockElectoralDataSource) -> None:
    bommanahalli = src.get_constituency("KA-151")
    assert bommanahalli is not None
    assert bommanahalli.ac_name == "Bommanahalli"
    assert bommanahalli.state == "KA"
    assert src.get_constituency("ZZ-999") is None


# 9. get_history returns 5 elections, year-descending.
def test_get_history_year_descending(src: MockElectoralDataSource) -> None:
    h = src.get_history("KA-151")
    assert len(h) == 5
    years = [e.year for e in h]
    assert years == sorted(years, reverse=True)
    # Also verify the n-cap works.
    assert len(src.get_history("KA-151", n=2)) == 2


# 10. pin_to_ac happy + unknown PIN.
def test_pin_to_ac(src: MockElectoralDataSource) -> None:
    # Riya's PIN should map to her AC.
    assert src.pin_to_ac("560068") == "KA-151"
    assert src.pin_to_ac("999999") is None
    with pytest.raises(ValueError):
        src.pin_to_ac("abcdef")


# 11. Data integrity: every voter is_synthetic=True.
#     Non-negotiable per docs/DATA.md §4.
def test_every_voter_is_synthetic(src: MockElectoralDataSource) -> None:
    assert src.voters, "voter dataset must not be empty"
    bad = [v for v in src.voters.values() if v.is_synthetic is not True]
    assert not bad, f"{len(bad)} voters lack is_synthetic=True"


# 12. Data integrity: every accessibility block is synthetic AND every
#     election record has a non-empty source AND every voter's booth_id
#     resolves AND every voter's ac_code exists.
def test_data_integrity(src: MockElectoralDataSource) -> None:
    for b in src.booths.values():
        assert b.accessibility.synthetic is True, f"booth {b.booth_id}"
        assert b.source, f"booth {b.booth_id} missing source"

    for c in src.constituencies.values():
        for e in c.elections:
            assert e.source, f"election {c.ac_code}/{e.year} missing source"

    ac_set = set(src.constituencies)
    booth_set = set(src.booths)
    for v in src.voters.values():
        assert v.ac_code in ac_set, f"voter {v.epic_number} ac_code orphan"
        assert v.booth_id in booth_set, f"voter {v.epic_number} booth_id orphan"
