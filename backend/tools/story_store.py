"""Persist completed StoryAgent narratives for shareable permalinks.

Today: Cloud Storage upload + signed URL when STORAGE_BUCKET is set,
JSON file under backend/data/_stories/ otherwise. Phase 6 wires the
permalink page (`app/story/[ac_code]/page.tsx`) on the frontend.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tools._envelope import err, ok

log = logging.getLogger(__name__)
LOCAL_STORY_DIR = Path(__file__).resolve().parents[1] / "data" / "_stories"
LOCAL_STORY_DIR.mkdir(parents=True, exist_ok=True)


def store_story(session_id: str, ac_code: str, narrative: str, cover_url: str = "", audio_url: str = "") -> dict:
    if not session_id or not ac_code or not narrative:
        return err("missing_fields", "Internal: session_id, ac_code, narrative are required.")
    payload = {
        "session_id": session_id,
        "ac_code": ac_code,
        "narrative": narrative,
        "cover_url": cover_url,
        "audio_url": audio_url,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    bucket = os.environ.get("STORAGE_BUCKET")
    filename = f"{ac_code}.json"
    if bucket:
        try:
            from google.cloud import storage  # noqa: WPS433
            client = storage.Client()
            blob = client.bucket(bucket).blob(f"story/{filename}")
            blob.upload_from_string(json.dumps(payload, ensure_ascii=False), content_type="application/json")
            expires = datetime.now(timezone.utc) + timedelta(days=30)
            permalink = blob.generate_signed_url(version="v4", expiration=expires, method="GET")
            return ok(permalink=permalink, storage="cloud")
        except Exception as e:
            log.warning("story upload failed (%s); writing locally", e)
    out_path = LOCAL_STORY_DIR / filename
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return ok(permalink=out_path.as_uri(), storage="local")
