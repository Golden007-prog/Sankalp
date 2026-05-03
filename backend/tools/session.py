"""Session CRUD on Firestore with in-memory fallback.

The Orchestrator owns this. Specialists never touch Firestore —
they return state-deltas and the Orchestrator persists them.

Per docs/ARCHITECTURE.md §12, Firestore unavailability degrades to an
in-process dict (warning logged; user told history won't persist).
"""
from __future__ import annotations

import logging
import os
import secrets
from typing import Optional

from schemas.session import SessionState
from tools._envelope import err, ok

log = logging.getLogger(__name__)
COLLECTION = "sessions"


class _InMemoryStore:
    """Fallback when Firestore is unreachable. Process-local."""

    def __init__(self) -> None:
        self._data: dict[str, dict] = {}

    def get(self, sid: str) -> Optional[dict]:
        return self._data.get(sid)

    def set(self, sid: str, doc: dict) -> None:
        self._data[sid] = doc

    def delete(self, sid: str) -> None:
        self._data.pop(sid, None)


_inmem = _InMemoryStore()
_firestore_client = None  # lazy
_firestore_disabled = False


def _client():
    global _firestore_client, _firestore_disabled
    if _firestore_disabled:
        return None
    if _firestore_client is None:
        try:
            from google.cloud import firestore  # noqa: WPS433
            project = os.environ.get("FIRESTORE_PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT")
            _firestore_client = firestore.Client(project=project)
        except Exception as e:  # network/auth/etc.
            log.warning("firestore unavailable, using in-memory fallback: %s", e)
            _firestore_disabled = True
            return None
    return _firestore_client


def new_session_id() -> str:
    """256-bit URL-safe opaque session id (docs/ARCHITECTURE.md §10)."""
    return secrets.token_urlsafe(32)


def load_session(session_id: str) -> dict:
    """Return SessionState dict; auto-create when missing.

    Any Firestore failure (auth, network, perms) flips this process to
    in-memory mode for the rest of its lifetime — see ARCHITECTURE §12.
    """
    global _firestore_disabled
    client = _client()
    if client is not None:
        try:
            snap = client.collection(COLLECTION).document(session_id).get()
            if snap.exists:
                return ok(state=SessionState.model_validate(snap.to_dict(), strict=False).model_dump(mode="json"))
        except Exception as e:
            log.warning("firestore unavailable (%s); switching to in-memory store for this process", e)
            _firestore_disabled = True
            client = None

    if client is None:
        doc = _inmem.get(session_id)
        if doc is not None:
            return ok(state=SessionState.model_validate(doc, strict=False).model_dump(mode="json"))

    fresh = SessionState.new(session_id)
    _persist(session_id, fresh.model_dump(mode="json"))
    return ok(state=fresh.model_dump(mode="json"), created=True)


def update_session(session_id: str, delta: dict) -> dict:
    """Apply a partial update and persist. delta keys must be SessionState fields."""
    if not isinstance(delta, dict):
        return err("delta_not_dict", "I had trouble saving your update.")
    loaded = load_session(session_id)
    if not loaded.get("ok"):
        return loaded
    state = SessionState.model_validate(loaded["state"], strict=False)
    try:
        new_state = state.with_delta(delta)
    except Exception as e:
        return err(f"delta_invalid: {e}", "Couldn't apply that update — please try again.")
    _persist(session_id, new_state.model_dump(mode="json"))
    return ok(state=new_state.model_dump(mode="json"))


def _persist(session_id: str, doc: dict) -> None:
    global _firestore_disabled
    client = _client()
    if client is not None:
        try:
            client.collection(COLLECTION).document(session_id).set(doc)
            return
        except Exception as e:
            log.warning("firestore persist unavailable (%s); switching to in-memory", e)
            _firestore_disabled = True
    _inmem.set(session_id, doc)
