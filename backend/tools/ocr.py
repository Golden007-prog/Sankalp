"""Cloud Vision OCR for EPIC card photos.

Multi-strategy parser:
  1. DOCUMENT_TEXT_DETECTION (best for printed cards) → regex on full_text
  2. TEXT_DETECTION fallback (broader detection) when DOCUMENT mode is empty
  3. Char-substitution heuristic for OCR near-misses (O↔0, I↔1, B↔8, S↔5, Z↔2)
  4. Cross-check against MockElectoralDataSource — boost confidence + surface
     the matched name when the parsed EPIC hits a known voter

Returns a graceful-degradation envelope when the Vision client is unreachable
(auth/quota) — see ARCHITECTURE.md §12.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from tools._envelope import err, ok

log = logging.getLogger(__name__)

# Strict EPIC: 3 uppercase letters + 7 digits, optional whitespace between.
_EPIC_RE = re.compile(r"\b([A-Z]{3})[\s\-]?([0-9]{7})\b")
# Loose EPIC pattern that accepts O/I/B/S/Z confusable digits — used only
# when the strict pass yields nothing.
_EPIC_LOOSE = re.compile(r"\b([A-Z]{3})[\s\-]?([A-Z0-9]{7})\b")

# Cheap heuristic: digits the OCR commonly emits as letters when the source
# is dot-matrix printed onto a glossy laminate.
_DIGIT_FIX = str.maketrans({"O": "0", "I": "1", "B": "8", "S": "5", "Z": "2"})


def detect_epic_text(image_bytes: bytes) -> dict:
    if not image_bytes:
        return err("empty_image", "I didn't get an image — please retake the photo.")
    try:
        from google.cloud import vision  # noqa: WPS433
    except Exception:
        return ok(
            degraded=True, raw_text="", epic_number=None, confidence=0.0,
            strategy_used=None, alternatives=[],
        )

    try:
        client = vision.ImageAnnotatorClient()
        image = vision.Image(content=image_bytes)
        return _run_strategies(client, image, vision)
    except Exception as e:
        log.exception("vision OCR failed")
        return err(
            f"vision_call: {e}",
            "I had trouble reading the photo — please try again with better lighting.",
        )


def _run_strategies(client, image, vision) -> dict:  # type: ignore[no-untyped-def]
    """Try DOCUMENT first; fall back to TEXT if it didn't yield anything."""
    # ----- Strategy 1: DOCUMENT_TEXT_DETECTION -----
    resp = client.document_text_detection(image=image)
    if resp.error and resp.error.message:
        return err(
            f"vision_api: {resp.error.message}",
            "I had trouble reading the photo — please try again with better lighting.",
        )
    doc_text = resp.full_text_annotation.text if resp.full_text_annotation else ""
    epic, base_conf, alts = _parse_with_heuristics(doc_text)

    if epic and base_conf >= 0.7:
        return _finalize(doc_text, epic, base_conf, alts, "document_text_detection")

    # ----- Strategy 2: TEXT_DETECTION (fallback) -----
    try:
        text_resp = client.text_detection(image=image)
        text_text = text_resp.full_text_annotation.text if text_resp.full_text_annotation else ""
        if text_text:
            t_epic, t_conf, t_alts = _parse_with_heuristics(text_text)
            if t_epic and t_conf > base_conf:
                merged_alts = sorted({*(alts or []), *(t_alts or [])})
                return _finalize(text_text, t_epic, t_conf, merged_alts, "text_detection_fallback")
    except Exception:  # pragma: no cover  (network flakiness on fallback path)
        log.exception("text_detection fallback failed")

    if epic:
        return _finalize(doc_text, epic, base_conf, alts, "document_text_detection")

    # No EPIC found in either strategy.
    return ok(
        degraded=False, raw_text=doc_text, epic_number=None,
        confidence=0.0, strategy_used="none", alternatives=[],
    )


def _parse_with_heuristics(text: str) -> tuple[Optional[str], float, list[str]]:
    """Return (best_guess, confidence, alternatives) from raw OCR text."""
    if not text:
        return None, 0.0, []
    upper = text.upper()
    alternatives: list[str] = []

    # Pass 1 — strict format, highest confidence.
    m = _EPIC_RE.search(upper)
    if m:
        epic = f"{m.group(1)}{m.group(2)}"
        return epic, 0.85, alternatives

    # Pass 2 — loose format + digit-confusable substitution.
    for lm in _EPIC_LOOSE.finditer(upper):
        prefix = lm.group(1)
        suffix_raw = lm.group(2)
        fixed = suffix_raw.translate(_DIGIT_FIX)
        if fixed.isdigit() and len(fixed) == 7:
            candidate = f"{prefix}{fixed}"
            if not alternatives:
                alternatives.append(candidate)
            return candidate, 0.65, alternatives

    return None, 0.0, alternatives


def _finalize(
    raw_text: str, epic: str, confidence: float, alternatives: list[str], strategy: str,
) -> dict:
    matched_name: Optional[str] = None
    boosted = confidence
    try:
        from tools.data_source import get_data_source  # noqa: WPS433
        rec = get_data_source().search_by_epic(epic)
        if rec is not None:
            matched_name = rec.name
            boosted = min(0.97, confidence + 0.05)
    except Exception:
        # Cross-check is best-effort — never fail OCR on dataset errors.
        pass

    payload = ok(
        degraded=False,
        raw_text=raw_text,
        epic_number=epic,
        confidence=round(boosted, 2),
        strategy_used=strategy,
        alternatives=alternatives,
    )
    if matched_name is not None:
        payload["matched_name"] = matched_name
    return payload
