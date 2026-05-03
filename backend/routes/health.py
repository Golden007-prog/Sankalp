"""Health probe.

Mounted at /api/healthz because bare /healthz is reserved by the Google
Frontend on *.run.app — see Phase 0 commit message.
"""
from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter

VERSION = "0.3.0"
SERVICE_NAME = "sankalp-backend"

router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthz() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": SERVICE_NAME,
        "version": VERSION,
        "git_sha": os.environ.get("GIT_SHA", "dev"),
        "phase": "3",
    }
