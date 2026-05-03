"""POST /api/chat — SSE streaming endpoint.

Body: {message, session_id?, language?}
Response: text/event-stream with stages lang_detect, routing, specialist:<name>,
          tool_call, delta, final.

Session id is minted server-side when not supplied and returned via the
X-Sankalp-Session-Id response header so the frontend can persist it in
localStorage.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from sse.bridge import stream_chat
from tools.session import new_session_id

log = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: Optional[str] = None
    language: Optional[str] = None


@router.post("/chat")
async def chat(body: ChatRequest, request: Request) -> EventSourceResponse:
    rid = getattr(request.state, "request_id", "no-id")
    sid = body.session_id or new_session_id()
    log.info(
        "chat_open",
        extra={"request_id": rid, "session_id": sid, "path": "/api/chat",
               "method": "POST", "language": body.language},
    )
    generator = stream_chat(
        message=body.message,
        session_id=sid,
        language_override=body.language,
        request_id=rid,
    )
    response = EventSourceResponse(
        generator,
        ping=15,  # heartbeat to keep proxies alive on long story streams
        headers={"X-Sankalp-Session-Id": sid},
    )
    return response
