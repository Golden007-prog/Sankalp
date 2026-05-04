"""GET /api/constituency/{ac_code} — read-only lookup powering the
permalink page's StoryCanvas. Streams a Constituency model_dump as JSON.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from tools.data_source import get_data_source

router = APIRouter(prefix="/constituency", tags=["constituency"])


@router.get("/{ac_code}")
def get_constituency_route(ac_code: str) -> dict:
    src = get_data_source()
    c = src.get_constituency(ac_code)
    if c is None:
        raise HTTPException(status_code=404, detail=f"AC {ac_code} not in demo dataset")
    return c.model_dump(mode="json", exclude_none=True)
