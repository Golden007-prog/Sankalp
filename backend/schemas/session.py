"""Sankalp session-state contract.

One Pydantic model. Owned by the Orchestrator. Persisted to Firestore
with TTL=24h. See docs/ARCHITECTURE.md §5 + docs/AGENTS.md "Inter-agent
contracts".
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from .electoral import LanguageCode, RelationType, SeatType  # noqa: F401  (re-exports)

Intent = Literal[
    "register", "verify", "booth", "story",
    "smalltalk", "clarify", "switch_language", "unknown",
]
ChangeType = Literal["address", "name", "photo", "all"]


class FormState(BaseModel):
    """Partial Form 6 / Form 8 fill state. Survives across turns."""

    model_config = ConfigDict(extra="forbid")
    form_type: Optional[Literal["6", "8"]] = None
    change_type: Optional[ChangeType] = None
    full_name: Optional[str] = None
    full_name_native: Optional[str] = None
    dob: Optional[str] = None  # ISO YYYY-MM-DD; validated by RegistrationAgent tool
    gender: Optional[Literal["M", "F", "T"]] = None
    relation_type: Optional[Literal["father", "mother", "husband", "wife"]] = None
    relation_name: Optional[str] = None
    house: Optional[str] = None
    street: Optional[str] = None
    locality: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    ac_code: Optional[str] = None
    ac_name: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None
    disability_status: Optional[str] = None
    epic_number: Optional[str] = None  # Form 8: existing EPIC
    confirmed: bool = False


class VoterRecordPreview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    epic_number: str
    name: str
    ac_code: str
    booth_id: Optional[str] = None


class BoothPreview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    booth_id: str
    name: str
    address: str
    lat: float
    lng: float


class StoryPreview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ac_code: str
    permalink: Optional[str] = None
    cover_url: Optional[str] = None
    audio_url: Optional[str] = None


class OcrResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    epic_number: Optional[str] = None
    name: Optional[str] = None
    raw_text: Optional[str] = None
    confidence: float = 0.0


class SessionState(BaseModel):
    """Single source of truth for one user session. Document ID is the
    session_id; expires_at drives the Firestore TTL. No real PII."""

    model_config = ConfigDict(extra="forbid")
    # min_length=1 instead of 8 because the orchestrator's load_session
    # tool sometimes synthesises "default" as a placeholder session_id
    # (the LLM has no reliable way to know the real id); we let the bridge
    # rewrite to the real token before persisting.
    session_id: str = Field(min_length=1)
    language: LanguageCode = "en"
    last_intent: Optional[Intent] = None
    form_state: Optional[FormState] = None
    last_voter_record: Optional[VoterRecordPreview] = None
    last_booth: Optional[BoothPreview] = None
    last_story: Optional[StoryPreview] = None
    last_ocr: Optional[OcrResult] = None
    handoff_count: int = 0  # Per-turn counter, reset by Orchestrator each turn
    created_at: datetime
    expires_at: datetime  # +24h

    @classmethod
    def new(cls, session_id: str, language: LanguageCode = "en") -> SessionState:
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        return cls(
            session_id=session_id,
            language=language,
            created_at=now,
            expires_at=now + timedelta(hours=24),
        )

    def with_delta(self, delta: dict) -> SessionState:
        """Apply a partial-update dict and return a new SessionState.
        Used by the Orchestrator's update_session tool — it never mutates."""
        merged = self.model_dump()
        for k, v in delta.items():
            merged[k] = v
        return SessionState.model_validate(merged)
