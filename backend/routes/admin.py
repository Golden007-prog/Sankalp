"""GET /api/admin/costs?key=... — Phase 6 minimum-viable cost dashboard.

Aggregates Firestore `cost_log` documents for the last 24 hours into a
small JSON summary. Gated by a shared-secret query parameter
(`SANKALP_ADMIN_KEY` env). Phase-7 polish wires Firestore → BigQuery and
a real Looker Studio dashboard.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from statistics import median, quantiles

from fastapi import APIRouter, HTTPException, Query

log = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])


def _check_key(key: str) -> None:
    expected = os.environ.get("SANKALP_ADMIN_KEY")
    if not expected:
        raise HTTPException(status_code=503, detail="SANKALP_ADMIN_KEY unset")
    if key != expected:
        raise HTTPException(status_code=403, detail="invalid admin key")


@router.get("/costs")
def costs_summary(key: str = Query(...), hours: int = Query(default=24, ge=1, le=168)) -> dict:
    _check_key(key)
    try:
        from google.cloud import firestore  # noqa: WPS433
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"firestore_unavailable: {e}") from None

    project = os.environ.get("FIRESTORE_PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT")
    client = firestore.Client(project=project)
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    try:
        docs = list(
            client.collection("cost_log").where("created_at", ">=", since).stream()
        )
    except Exception as e:
        log.exception("cost_log query failed")
        raise HTTPException(status_code=502, detail=f"firestore_query: {e}") from None

    if not docs:
        return {
            "ok": True, "hours": hours, "session_count": 0, "request_count": 0,
            "total_tokens_in": 0, "total_tokens_out": 0,
            "latency_ms": {"p50": 0, "p95": 0},
            "by_agent": {}, "by_model": {},
        }

    rows = [d.to_dict() for d in docs]
    sessions = {r.get("session_id") for r in rows if r.get("session_id")}
    latencies = sorted(int(r.get("latency_ms") or 0) for r in rows)

    def _pct(latencies_sorted: list[int], pct: float) -> int:
        if not latencies_sorted:
            return 0
        idx = max(0, min(len(latencies_sorted) - 1, int(round(pct * (len(latencies_sorted) - 1)))))
        return latencies_sorted[idx]

    by_agent: dict[str, dict[str, int]] = {}
    by_model: dict[str, dict[str, int]] = {}
    for r in rows:
        a = r.get("agent", "unknown")
        m = r.get("model", "unknown")
        by_agent.setdefault(a, {"requests": 0, "tokens_in": 0, "tokens_out": 0})
        by_agent[a]["requests"] += 1
        by_agent[a]["tokens_in"] += int(r.get("tokens_in") or 0)
        by_agent[a]["tokens_out"] += int(r.get("tokens_out") or 0)
        by_model.setdefault(m, {"requests": 0, "tokens_in": 0, "tokens_out": 0})
        by_model[m]["requests"] += 1
        by_model[m]["tokens_in"] += int(r.get("tokens_in") or 0)
        by_model[m]["tokens_out"] += int(r.get("tokens_out") or 0)

    return {
        "ok": True,
        "hours": hours,
        "request_count": len(rows),
        "session_count": len(sessions),
        "total_tokens_in": sum(int(r.get("tokens_in") or 0) for r in rows),
        "total_tokens_out": sum(int(r.get("tokens_out") or 0) for r in rows),
        "latency_ms": {
            "p50": _pct(latencies, 0.5),
            "p95": _pct(latencies, 0.95),
            "max": latencies[-1] if latencies else 0,
        },
        "by_agent": by_agent,
        "by_model": by_model,
    }
