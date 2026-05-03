"""Cost-log entry — written once per /api/chat request.

Powers the Looker Studio dashboard wired in Phase 6 (ROADMAP.md Day 6).
No TTL on this collection — it's the audit trail for LLM spend across
the demo + judging window.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CostLogEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str
    session_id: str
    agent: str = Field(min_length=1)
    model: str = Field(min_length=1)
    tokens_in: int = Field(ge=0)
    tokens_out: int = Field(ge=0)
    tool_calls: list[str] = Field(default_factory=list)
    latency_ms: int = Field(ge=0)
    ok: bool = True
    error: Optional[str] = None
    intent: Optional[str] = None
    language: Optional[str] = None
    created_at: datetime
