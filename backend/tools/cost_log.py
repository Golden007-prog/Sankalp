"""Cost-log writer.

Single Firestore document per /api/chat invocation. Falls back to a
structured log line when Firestore is unavailable (ARCHITECTURE §12) so
the demo never blocks on persistence.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

from schemas.cost import CostLogEntry

log = logging.getLogger(__name__)
COLLECTION = "cost_log"

_client = None
_disabled = False


def _firestore():
    global _client, _disabled
    if _disabled:
        return None
    if _client is None:
        try:
            from google.cloud import firestore  # noqa: WPS433
            project = os.environ.get("FIRESTORE_PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT")
            _client = firestore.Client(project=project)
        except Exception as e:
            log.warning("cost_log firestore unavailable: %s", e)
            _disabled = True
            return None
    return _client


def write(entry: CostLogEntry) -> dict[str, Any]:
    """Persist a cost entry. Returns a small ack dict for testability."""
    global _disabled
    payload = entry.model_dump(mode="json")
    fs = _firestore()
    if fs is not None:
        try:
            fs.collection(COLLECTION).add(payload)
            return {"ok": True, "storage": "firestore"}
        except Exception as e:
            log.warning("cost_log firestore write failed (%s); logging instead", e)
            _disabled = True
    # Fallback: structured log line so the audit trail still exists in
    # Cloud Logging even when Firestore is unreachable.
    log.info("cost_log %s", json.dumps(payload, default=str))
    return {"ok": True, "storage": "log"}


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def make_entry(
    *, request_id: str, session_id: str, agent: str, model: str,
    tokens_in: int, tokens_out: int, latency_ms: int,
    tool_calls: Optional[list[str]] = None,
    intent: Optional[str] = None, language: Optional[str] = None,
    ok_flag: bool = True, error: Optional[str] = None,
) -> CostLogEntry:
    return CostLogEntry(
        request_id=request_id,
        session_id=session_id,
        agent=agent,
        model=model,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        tool_calls=tool_calls or [],
        latency_ms=latency_ms,
        ok=ok_flag,
        error=error,
        intent=intent,
        language=language,
        created_at=now_utc(),
    )
