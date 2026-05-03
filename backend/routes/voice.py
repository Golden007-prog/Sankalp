"""POST /api/voice/token — Phase 3 stub.

Real Gemini Live WebSocket bridge lands in Phase 4 alongside the
frontend voice button (ROADMAP.md Day 4). For now the route exists so
the contract surface is stable and the frontend can probe for capability.
"""
from __future__ import annotations

import os

from fastapi import APIRouter

router = APIRouter(prefix="/voice", tags=["voice"])


@router.post("/token")
def voice_token() -> dict:
    return {
        "ok": False,
        "phase": "3-stub",
        "user_message": "Voice is wired in Phase 4; please type your question for now.",
        "vertex_project": os.environ.get("GOOGLE_CLOUD_PROJECT"),
    }
