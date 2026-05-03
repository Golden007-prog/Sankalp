from __future__ import annotations

from datetime import date
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

EpicNumber = Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}\d{7}$")]
AcCode = Annotated[str, StringConstraints(min_length=1, max_length=8, strip_whitespace=True)]
Pincode = Annotated[str, StringConstraints(pattern=r"^\d{6}$")]

# ISO 3166-2:IN — 28 states + 8 UTs.
StateCode = Literal[
    "AN", "AP", "AR", "AS", "BR", "CG", "CH", "DH", "DL", "GA", "GJ", "HP",
    "HR", "JH", "JK", "KA", "KL", "LA", "LD", "MH", "ML", "MN", "MP", "MZ",
    "NL", "OR", "PB", "PY", "RJ", "SK", "TG", "TN", "TR", "UK", "UP", "WB",
]

# Languages with TTS coverage at launch (PRD §5.1) plus a few we'll wire later.
LanguageCode = Literal[
    "en", "hi", "bn", "ta", "kn", "te", "mr", "gu", "pa", "or", "as", "ml", "ur",
]

Gender = Literal["M", "F", "T"]
SeatType = Literal["GEN", "SC", "ST"]
ElectionType = Literal["Vidhan Sabha", "Lok Sabha"]
RelationType = Literal["father", "mother", "husband", "wife"]


class Address(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    house: str
    street: str
    locality: str
    city: str
    state: StateCode
    pincode: Pincode


class ElectionRecord(BaseModel):
    """One past election in a constituency. Either real (with ECI source)
    or synthesized for demo (is_synthetic_election=True + synthesis_note)."""

    model_config = ConfigDict(strict=True, extra="forbid")
    year: int = Field(ge=1990, le=2030)
    type: ElectionType
    winner_party: str
    runner_up_party: str
    win_margin: int = Field(ge=0)
    turnout_pct: float = Field(ge=0.0, le=100.0)
    total_votes_polled: int = Field(ge=0)
    source: str = Field(min_length=3)
    is_synthetic_election: bool = False
    synthesis_note: Optional[str] = None

    @field_validator("synthesis_note")
    @classmethod
    def _note_only_if_synthetic(cls, v: Optional[str], info):
        is_synth = info.data.get("is_synthetic_election", False)
        if is_synth and not v:
            raise ValueError("synthesis_note required when is_synthetic_election=True")
        if not is_synth and v:
            raise ValueError("synthesis_note must be empty when election is real")
        return v


class Demographics(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    literacy_pct: float = Field(ge=0.0, le=100.0)
    urban_pct: float = Field(ge=0.0, le=100.0)
    primary_languages: list[LanguageCode] = Field(min_length=1)
    is_synthetic: bool = False
    source: str = Field(min_length=3)


class Provenance(BaseModel):
    """Per-constituency disclosure block. Surfaced in the UI as the 'demo
    data' chip. See docs/DATA.md §5."""

    model_config = ConfigDict(strict=True, extra="forbid")
    name_and_codes: str
    elections: str
    demographics: str
    booths: str
    notes: Optional[str] = None


class Constituency(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    ac_code: AcCode
    ac_name: str
    ac_name_native: Optional[str] = None
    state: StateCode
    state_name: str
    district: str
    lok_sabha_code: Optional[str] = None
    lok_sabha_name: Optional[str] = None
    type: SeatType
    total_electors: int = Field(ge=1000)
    male_electors: int = Field(ge=0)
    female_electors: int = Field(ge=0)
    third_gender_electors: int = Field(ge=0, default=0)
    total_booths: int = Field(ge=1)
    centroid_lat: float = Field(ge=6.0, le=37.5)
    centroid_lng: float = Field(ge=68.0, le=97.5)
    elections: list[ElectionRecord] = Field(min_length=1)
    demographics: Demographics
    key_landmarks: list[str] = Field(default_factory=list)
    provenance: Provenance

    @field_validator("elections")
    @classmethod
    def _elections_descending(cls, v: list[ElectionRecord]) -> list[ElectionRecord]:
        if v != sorted(v, key=lambda e: e.year, reverse=True):
            raise ValueError("elections must be sorted year-descending")
        return v


class VoterRecord(BaseModel):
    """Synthetic voter record. is_synthetic is forced True — no real voter
    is in this dataset (see docs/DATA.md §4)."""

    model_config = ConfigDict(strict=True, extra="forbid")
    epic_number: EpicNumber
    name: str
    name_native: Optional[str] = None
    dob: date
    gender: Gender
    relation_type: RelationType
    relation_name: str
    address: Address
    ac_code: AcCode
    booth_id: str
    is_synthetic: Literal[True] = True


class AccessibilityFlags(BaseModel):
    """ECI does not publish booth-level accessibility data publicly.
    `synthetic` is forced True — see docs/DATA.md §4."""

    model_config = ConfigDict(strict=True, extra="forbid")
    wheelchair: bool
    ramp: bool
    ground_floor: bool
    language_assistance: list[LanguageCode] = Field(default_factory=list)
    sign_language: bool = False
    braille_ballot: bool = False
    synthetic: Literal[True] = True


class Booth(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    booth_id: str
    ac_code: AcCode
    name: str
    address: str
    lat: float
    lng: float
    accessibility: AccessibilityFlags
    voting_hours: str = "07:00-18:00"
    source: str = Field(min_length=3)


class DemoPersona(BaseModel):
    """Scripted personas baked into the synthetic roll so smoke tests find
    them deterministically. See docs/DATA.md §2.2."""

    model_config = ConfigDict(strict=True, extra="forbid")
    persona_id: str
    epic_number: EpicNumber
    name: str
    journey: Literal["verify_happy", "form8_address", "story", "dedup"]
    notes: str
