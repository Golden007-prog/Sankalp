from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='{"level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
)
log = logging.getLogger("sankalp")

VERSION = "0.0.1"
GIT_SHA = os.getenv("GIT_SHA", "dev")
SERVICE_NAME = "sankalp-backend"

app = FastAPI(title="Sankalp Backend", version=VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://sankalp-frontend-*.run.app",
    ],
    allow_origin_regex=r"https://sankalp-frontend-.*\.run\.app",
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/api/healthz")
def healthz() -> dict[str, Any]:
    # External path is /api/healthz; bare /healthz is reserved by Google
    # Frontend on *.run.app and never reaches the container.
    return {
        "status": "ok",
        "service": SERVICE_NAME,
        "version": VERSION,
        "git_sha": GIT_SHA,
    }


@app.get("/")
def root() -> dict[str, str]:
    return {"service": SERVICE_NAME, "message": "Sankalp backend is up."}
