"""Permalink reads:

  GET /api/story/{ac_code}             → JSON narrative + cover_url + audio_url
  GET /api/story/{ac_code}/cover.png   → streams the PNG from private GCS

The bucket stays private; the runtime SA reads it on the user's behalf.
404 when the story or cover doesn't exist yet (StoryAgent hasn't run).
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Iterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

log = logging.getLogger(__name__)
router = APIRouter(prefix="/story", tags=["story"])

_AC_RE = re.compile(r"^[A-Z]{2}-\d{1,4}$")


def _bucket_name() -> str:
    bucket = os.environ.get("STORAGE_BUCKET")
    if not bucket:
        raise HTTPException(status_code=503, detail="STORAGE_BUCKET unset")
    return bucket


def _gcs_blob(path: str):
    from google.cloud import storage  # noqa: WPS433
    client = storage.Client()
    return client.bucket(_bucket_name()).blob(path)


@router.get("/{ac_code}")
def get_story(ac_code: str) -> dict:
    if not _AC_RE.match(ac_code):
        raise HTTPException(status_code=400, detail="invalid ac_code format")
    blob = _gcs_blob(f"story/{ac_code}.json")
    if not blob.exists():
        raise HTTPException(status_code=404, detail=f"no story for {ac_code} yet")
    try:
        body = blob.download_as_bytes()
    except Exception as e:
        log.exception("story read failed")
        raise HTTPException(status_code=502, detail=f"gcs read: {e}") from None
    try:
        return json.loads(body)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"corrupt story json: {e}") from None


@router.get("/{ac_code}/cover.png")
def get_cover(ac_code: str) -> StreamingResponse:
    if not _AC_RE.match(ac_code):
        raise HTTPException(status_code=400, detail="invalid ac_code format")
    blob = _gcs_blob(f"story/{ac_code}/cover.png")
    if not blob.exists():
        raise HTTPException(status_code=404, detail=f"no cover for {ac_code}")
    try:
        body = blob.download_as_bytes()
    except Exception as e:
        log.exception("cover read failed")
        raise HTTPException(status_code=502, detail=f"gcs read: {e}") from None

    def _stream() -> Iterator[bytes]:
        yield body

    return StreamingResponse(
        _stream(),
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )
