"""POST /api/vision/epic — OCR an EPIC card photo and persist the parse
into session_state.last_ocr so the next /api/chat turn auto-routes to
VerificationAgent.

Body: multipart/form-data with `file` (image/jpeg|image/png), optional `session_id`.
Response: {ok, epic_number, raw_text, confidence, session_id}.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from schemas.session import OcrResult
from tools.ocr import detect_epic_text
from tools.session import new_session_id, update_session

log = logging.getLogger(__name__)
router = APIRouter(prefix="/vision", tags=["vision"])

MAX_BYTES = 8 * 1024 * 1024  # 8 MB


@router.post("/epic")
async def epic_ocr(
    request: Request,
    file: UploadFile = File(...),
    session_id: Optional[str] = Form(default=None),
) -> dict:
    rid = getattr(request.state, "request_id", "no-id")
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=415, detail=f"unsupported content_type: {file.content_type}")
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="empty file")
    if len(raw) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="image too large; max 8 MB")

    sid = session_id or new_session_id()
    result = detect_epic_text(raw)
    log.info(
        "vision_epic",
        extra={"request_id": rid, "session_id": sid, "path": "/api/vision/epic",
               "method": "POST", "status": 200},
    )
    if result.get("ok"):
        # Persist into session_state.last_ocr so the next chat turn routes
        # to VerificationAgent automatically.
        ocr = OcrResult(
            epic_number=result.get("epic_number"),
            raw_text=result.get("raw_text", ""),
            confidence=float(result.get("confidence", 0.0)),
        )
        update_session(sid, {"last_ocr": ocr.model_dump(mode="json")})
    return {**result, "session_id": sid}
