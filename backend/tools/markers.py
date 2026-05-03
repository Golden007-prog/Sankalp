"""Structured marker parsing for inter-agent and agent-to-frontend
communication. See docs/AGENTS.md.

Marker shapes:
  [HANDOFF intent="..." reason="..."]
  [PDF_READY url="..." form_type="6" filename="..."]
  [VOTER_RECORD epic="..." name="..." ac="..." booth="..."]
  [BOOTH_CARD booth_id="..." address="..." lat=... lng=... ...]
  [STORY ac_code="..." cover_url="..." audio_url="..." permalink="..."]

The Orchestrator strips HANDOFF markers from the user-facing stream
and re-routes. The four others pass through to the frontend, which
parses them into rich React components in Phase 4.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

# kw="value" pairs (quoted) and kw=value (unquoted scalars like floats/ints/bools)
_KV_RE = re.compile(r'(\w+)=(?:"((?:[^"\\]|\\.)*)"|([^\s\]]+))')

_HANDOFF_RE = re.compile(r"\[HANDOFF\s+([^\]]*)\]")
_PDF_READY_RE = re.compile(r"\[PDF_READY\s+([^\]]*)\]")
_VOTER_RECORD_RE = re.compile(r"\[VOTER_RECORD\s+([^\]]*)\]")
_BOOTH_CARD_RE = re.compile(r"\[BOOTH_CARD\s+([^\]]*)\]")
_STORY_RE = re.compile(r"\[STORY\s+([^\]]*)\]")


def _parse_kv(body: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for m in _KV_RE.finditer(body):
        key = m.group(1)
        val = m.group(2) if m.group(2) is not None else m.group(3)
        out[key] = val
    return out


@dataclass(frozen=True)
class Handoff:
    intent: str
    reason: str

    @classmethod
    def parse(cls, text: str) -> Optional[Handoff]:
        m = _HANDOFF_RE.search(text)
        if not m:
            return None
        kv = _parse_kv(m.group(1))
        intent = kv.get("intent")
        if not intent:
            return None
        return cls(intent=intent, reason=kv.get("reason", ""))


def strip_handoff(text: str) -> str:
    """Remove HANDOFF markers from user-facing text."""
    return _HANDOFF_RE.sub("", text).strip()


def find_pdf_ready(text: str) -> Optional[dict[str, str]]:
    m = _PDF_READY_RE.search(text)
    return _parse_kv(m.group(1)) if m else None


def find_voter_record(text: str) -> Optional[dict[str, str]]:
    m = _VOTER_RECORD_RE.search(text)
    return _parse_kv(m.group(1)) if m else None


def find_booth_card(text: str) -> Optional[dict[str, str]]:
    m = _BOOTH_CARD_RE.search(text)
    return _parse_kv(m.group(1)) if m else None


def find_story(text: str) -> Optional[dict[str, str]]:
    m = _STORY_RE.search(text)
    return _parse_kv(m.group(1)) if m else None


def emit_handoff(intent: str, reason: str) -> str:
    return f'[HANDOFF intent="{intent}" reason="{_escape(reason)}"]'


def emit_voter_record(epic: str, name: str, ac: str, booth: str) -> str:
    return (
        f'[VOTER_RECORD epic="{_escape(epic)}" name="{_escape(name)}" '
        f'ac="{_escape(ac)}" booth="{_escape(booth)}"]'
    )


def emit_pdf_ready(url: str, form_type: str, filename: str) -> str:
    return (
        f'[PDF_READY url="{_escape(url)}" form_type="{form_type}" '
        f'filename="{_escape(filename)}"]'
    )


def emit_booth_card(
    booth_id: str, address: str, lat: float, lng: float,
    wheelchair: bool, language_assist: str,
    eta_walk: str = "", eta_transit: str = "",
) -> str:
    return (
        f'[BOOTH_CARD booth_id="{_escape(booth_id)}" '
        f'address="{_escape(address)}" lat={lat} lng={lng} '
        f'wheelchair={"true" if wheelchair else "false"} '
        f'language_assist="{_escape(language_assist)}" '
        f'eta_walk="{eta_walk}" eta_transit="{eta_transit}"]'
    )


def emit_story(
    ac_code: str, cover_url: str = "", audio_url: str = "", permalink: str = "",
) -> str:
    return (
        f'[STORY ac_code="{_escape(ac_code)}" '
        f'cover_url="{_escape(cover_url)}" '
        f'audio_url="{_escape(audio_url)}" '
        f'permalink="{_escape(permalink)}"]'
    )


def _escape(s: str) -> str:
    return s.replace('"', '\\"')
