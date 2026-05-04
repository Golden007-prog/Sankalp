"""Imagen 3 cover generation for StoryAgent.

Phase 6 hardening:
  - Forbidden-keyword pre-filter (political/religious imagery)
  - Process-level dev cap (env `SANKALP_IMAGEN_DEV_CAP`, default 10)
  - Optional cover_key kwarg → blob `story/{cover_key}/cover.png`,
    so the StoryAgent's permalink-page renders the same cover the chat
    bubble already shows
  - Bucket /story/ prefix is public-read (DEPLOYMENT.md §2.4) → emit
    a stable HTTPS URL instead of a 1-hour signed URL
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Optional

from tools._envelope import err, ok

log = logging.getLogger(__name__)

_FORBIDDEN = (
    "flag", "party", "candidate", "politician", "vote for", "election rally",
    "religious", "temple", "mosque", "church", "gurudwara", "saint",
)

_lock = Lock()
_calls_this_process = 0


def _dev_cap() -> int:
    try:
        return int(os.environ.get("SANKALP_IMAGEN_DEV_CAP", "10"))
    except ValueError:
        return 10


def imagen_cover(
    prompt: str,
    session_id: Optional[str] = None,
    cover_key: Optional[str] = None,
) -> dict:
    if any(bad in prompt.lower() for bad in _FORBIDDEN):
        return err(
            "forbidden_prompt",
            "I can't generate political or religious imagery — try a landscape or cityscape prompt.",
        )

    global _calls_this_process
    cap = _dev_cap()
    with _lock:
        if _calls_this_process >= cap:
            return err(
                "dev_cap_reached",
                f"Imagen dev cap ({cap}) reached for this process; cover skipped.",
            )

    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    bucket = os.environ.get("STORAGE_BUCKET")
    if not project or not bucket:
        return ok(
            degraded=True, image_url=None, prompt=prompt,
            note="Imagen requires GOOGLE_CLOUD_PROJECT + STORAGE_BUCKET.",
        )

    try:
        from google import genai  # noqa: WPS433
        from google.genai import types as genai_types  # noqa: WPS433
        from google.cloud import storage  # noqa: WPS433
    except Exception as e:
        return ok(degraded=True, image_url=None, prompt=prompt, note=f"sdk_unavailable: {e}")

    try:
        client = genai.Client(vertexai=True, project=project, location=location)
        result = client.models.generate_images(
            model="imagen-3.0-generate-002",
            prompt=prompt,
            config=genai_types.GenerateImagesConfig(
                number_of_images=1,
                output_mime_type="image/png",
                aspect_ratio="1:1",
                safety_filter_level="BLOCK_LOW_AND_ABOVE",
                person_generation="DONT_ALLOW",
            ),
        )
        with _lock:
            _calls_this_process += 1

        if not result.generated_images:
            return err("no_image_returned", "Imagen returned no image — try a different prompt.")
        img_bytes = result.generated_images[0].image.image_bytes

        gcs = storage.Client(project=project)
        # Cover key — backend-mediated path under /api/story/{key}/cover.png
        # (bucket stays private; the FastAPI route streams the bytes).
        # The frontend renders through /api/proxy/story/{key}/cover.png.
        if cover_key:
            blob = gcs.bucket(bucket).blob(f"story/{cover_key}/cover.png")
            blob.upload_from_string(img_bytes, content_type="image/png")
            url = f"/api/story/{cover_key}/cover.png"
            return ok(
                degraded=False, image_url=url, prompt=prompt,
                calls_this_process=_calls_this_process, dev_cap=cap,
            )

        sid = session_id or "anonymous"
        blob = gcs.bucket(bucket).blob(f"sessions/{sid}/cover.png")
        blob.upload_from_string(img_bytes, content_type="image/png")
        expires = datetime.now(timezone.utc) + timedelta(hours=1)
        url = blob.generate_signed_url(version="v4", expiration=expires, method="GET")
        return ok(
            degraded=False, image_url=url, prompt=prompt,
            calls_this_process=_calls_this_process, dev_cap=cap,
        )
    except Exception as e:
        log.exception("imagen call failed")
        return err(f"imagen: {e}", "I couldn't generate the cover this time — text story still ready.")


def reset_call_counter() -> None:
    """Test-only: zero the in-process call counter."""
    global _calls_this_process
    with _lock:
        _calls_this_process = 0
