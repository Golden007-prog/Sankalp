"""Cloud Vision OCR for EPIC card photos.

Returns the EPIC fields VerificationAgent needs. When the Vision client
isn't reachable (auth/quota), returns a `degraded` envelope so the
camera flow can fall back to manual entry per ARCHITECTURE.md §12.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from tools._envelope import err, ok

log = logging.getLogger(__name__)

_EPIC_RE = re.compile(r"\b([A-Z]{3}[0-9]{7})\b")


def detect_epic_text(image_bytes: bytes) -> dict:
    if not image_bytes:
        return err("empty_image", "I didn't get an image — please retake the photo.")
    try:
        from google.cloud import vision  # noqa: WPS433
    except Exception:
        return ok(degraded=True, raw_text="", epic_number=None, confidence=0.0)
    try:
        client = vision.ImageAnnotatorClient()
        image = vision.Image(content=image_bytes)
        resp = client.document_text_detection(image=image)
        if resp.error and resp.error.message:
            return err(f"vision_api: {resp.error.message}",
                       "I had trouble reading the photo — please try again with better lighting.")
        text = resp.full_text_annotation.text if resp.full_text_annotation else ""
    except Exception as e:
        log.exception("vision OCR failed")
        return err(f"vision_call: {e}",
                   "I had trouble reading the photo — please try again with better lighting.")

    epic = _extract_epic(text)
    return ok(
        degraded=False,
        raw_text=text,
        epic_number=epic,
        confidence=0.85 if epic else 0.0,
    )


def _extract_epic(text: str) -> Optional[str]:
    if not text:
        return None
    m = _EPIC_RE.search(text.upper())
    return m.group(1) if m else None
