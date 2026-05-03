"""Sankalp FastAPI app.

Lifespan loads the in-memory MockElectoralDataSource once per process
(target <50 ms data load+index, see DATA.md §7).
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from middleware.access_log import JsonAccessLogMiddleware
from middleware.json_logging import install as install_json_logging
from middleware.request_id import RequestIdMiddleware
from routes.chat import router as chat_router
from routes.health import router as health_router
from routes.vision import router as vision_router
from routes.voice import router as voice_router
from tools.data_source import get_data_source

install_json_logging(level=os.environ.get("LOG_LEVEL", "INFO"))
log = logging.getLogger("sankalp.main")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    src = get_data_source()  # warms the singleton + indexes
    log.info(
        "boot_complete",
        extra={
            "agent": "system",
            "tokens_in": 0,
            "tokens_out": 0,
        },
    )
    log.info(
        "dataset_loaded constituencies=%d voters=%d booths=%d",
        len(src.constituencies),
        len(src.voters),
        len(src.booths),
    )
    yield


app = FastAPI(
    title="Sankalp Backend",
    version="0.3.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

# Middleware order (outermost first): CORS → request-id → access log.
# PII redaction lives at the JSON formatter layer (catches every record).
app.add_middleware(JsonAccessLogMiddleware)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://sankalp-frontend-93037232246.asia-south1.run.app",
    ],
    allow_origin_regex=r"https://sankalp-frontend-.*\.run\.app",
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Sankalp-Session-Id", "X-Request-Id"],
)

app.include_router(health_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(vision_router, prefix="/api")
app.include_router(voice_router, prefix="/api")


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "sankalp-backend", "message": "Sankalp backend is up.", "docs": "/api/docs"}
