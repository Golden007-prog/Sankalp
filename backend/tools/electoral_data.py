"""Electoral-data lookup interface + mock implementation.

The Sankalp agents talk only to `ElectoralDataSource`. Today the only
implementation is `MockElectoralDataSource` which reads three JSON files
written by `scripts/build_dataset.py`. Swapping in a real ECI partner
backend later means writing a new subclass; nothing north of this module
needs to change. See docs/DATA.md §8.
"""
from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from datetime import date
from pathlib import Path
from typing import Optional

from pydantic import TypeAdapter

from schemas.electoral import Booth, Constituency, ElectionRecord, VoterRecord

_CONSTITUENCY_LIST = TypeAdapter(list[Constituency])
_VOTER_LIST = TypeAdapter(list[VoterRecord])
_BOOTH_LIST = TypeAdapter(list[Booth])

log = logging.getLogger(__name__)

EPIC_RE = re.compile(r"^[A-Z]{3}\d{7}$")
PIN_RE = re.compile(r"^\d{6}$")


class ElectoralDataSource(ABC):
    """Stable contract every Sankalp agent depends on."""

    @abstractmethod
    def search_by_epic(self, epic_number: str) -> Optional[VoterRecord]: ...

    @abstractmethod
    def search_by_name_dob(self, name: str, dob: Optional[date] = None) -> list[VoterRecord]: ...

    @abstractmethod
    def search_by_pincode(self, pincode: str) -> list[VoterRecord]: ...

    @abstractmethod
    def lookup_booth_by_id(self, booth_id: str) -> Optional[Booth]: ...

    @abstractmethod
    def lookup_booth_by_voter(self, epic_number: str) -> Optional[Booth]: ...

    @abstractmethod
    def get_constituency(self, ac_code: str) -> Optional[Constituency]: ...

    @abstractmethod
    def get_history(self, ac_code: str, n: int = 5) -> list[ElectionRecord]: ...

    @abstractmethod
    def pin_to_ac(self, pincode: str) -> Optional[str]: ...

    @abstractmethod
    def all_constituency_codes(self) -> list[str]: ...


class MockElectoralDataSource(ElectoralDataSource):
    """In-memory mock backed by `backend/data/*.json`.

    Cold-start budget: under 50 ms on Cloud Run min instance per
    docs/DATA.md §7. Indexes are built once in __init__.
    """

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        self.data_dir = (
            Path(data_dir)
            if data_dir is not None
            else Path(__file__).resolve().parents[1] / "data"
        )
        self._load()

    def _load(self) -> None:
        # validate_json reads bytes directly into Pydantic instances —
        # ~5-8x faster than json.loads + per-record model_validate, and
        # ISO date strings are coerced to date() in this path.
        c_bytes = (self.data_dir / "constituencies.json").read_bytes()
        v_bytes = (self.data_dir / "electoral_roll.json").read_bytes()
        b_bytes = (self.data_dir / "booths.json").read_bytes()

        constituencies = _CONSTITUENCY_LIST.validate_json(c_bytes)
        voters = _VOTER_LIST.validate_json(v_bytes)
        booths = _BOOTH_LIST.validate_json(b_bytes)

        self.constituencies: dict[str, Constituency] = {c.ac_code: c for c in constituencies}
        self.voters: dict[str, VoterRecord] = {v.epic_number: v for v in voters}
        self.booths: dict[str, Booth] = {b.booth_id: b for b in booths}

        # Indexes.
        self.name_index: dict[str, list[str]] = {}
        for v in self.voters.values():
            self.name_index.setdefault(v.name.lower(), []).append(v.epic_number)

        self.pin_index: dict[str, str] = {}
        # Voter pincodes win when in conflict (most specific real signal).
        for v in self.voters.values():
            self.pin_index.setdefault(v.address.pincode, v.ac_code)

        self.pincode_to_voters: dict[str, list[str]] = {}
        for v in self.voters.values():
            self.pincode_to_voters.setdefault(v.address.pincode, []).append(v.epic_number)

        self.ac_to_booths: dict[str, list[str]] = {}
        for b in self.booths.values():
            self.ac_to_booths.setdefault(b.ac_code, []).append(b.booth_id)

        log.info(
            "loaded mock electoral data: %d constituencies, %d voters, %d booths",
            len(self.constituencies), len(self.voters), len(self.booths),
        )

    # ----- ElectoralDataSource impl -----

    def search_by_epic(self, epic_number: str) -> Optional[VoterRecord]:
        if not EPIC_RE.match(epic_number):
            raise ValueError(f"invalid EPIC format: {epic_number!r}")
        return self.voters.get(epic_number)

    def search_by_name_dob(
        self, name: str, dob: Optional[date] = None
    ) -> list[VoterRecord]:
        candidates = self.name_index.get(name.lower(), [])
        out = [self.voters[e] for e in candidates]
        if dob is not None:
            out = [v for v in out if v.dob == dob]
        return out

    def search_by_pincode(self, pincode: str) -> list[VoterRecord]:
        if not PIN_RE.match(pincode):
            raise ValueError(f"invalid PIN format: {pincode!r}")
        return [self.voters[e] for e in self.pincode_to_voters.get(pincode, [])]

    def lookup_booth_by_id(self, booth_id: str) -> Optional[Booth]:
        return self.booths.get(booth_id)

    def lookup_booth_by_voter(self, epic_number: str) -> Optional[Booth]:
        v = self.search_by_epic(epic_number)
        if v is None:
            return None
        return self.booths.get(v.booth_id)

    def get_constituency(self, ac_code: str) -> Optional[Constituency]:
        return self.constituencies.get(ac_code)

    def get_history(self, ac_code: str, n: int = 5) -> list[ElectionRecord]:
        c = self.constituencies.get(ac_code)
        if c is None:
            return []
        return c.elections[:n]

    def pin_to_ac(self, pincode: str) -> Optional[str]:
        if not PIN_RE.match(pincode):
            raise ValueError(f"invalid PIN format: {pincode!r}")
        return self.pin_index.get(pincode)

    def all_constituency_codes(self) -> list[str]:
        return list(self.constituencies.keys())
