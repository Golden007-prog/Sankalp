"""Tool result envelope.

Every Sankalp tool returns either:

  {"ok": True,  ...payload...}
  {"ok": False, "error": "...internal", "user_message": "...localised"}

When an agent sees `ok=False`, it surfaces `user_message` in the user's
language and offers retry-or-pivot — never raises through to the user.
See docs/AGENTS.md "Inter-agent contracts → Error envelope".
"""
from __future__ import annotations

from typing import Any


def ok(**payload: Any) -> dict[str, Any]:
    return {"ok": True, **payload}


def err(error: str, user_message: str) -> dict[str, Any]:
    return {"ok": False, "error": error, "user_message": user_message}


def is_ok(envelope: dict[str, Any]) -> bool:
    return bool(envelope.get("ok"))
