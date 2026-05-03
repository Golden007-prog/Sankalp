"""ADK event stream → SSE stage events.

The SSE contract the Phase-4 frontend depends on:

  event: lang_detect          data: {"language": "hi"}
  event: routing              data: {"intent": "register"}
  event: specialist:registration  data: {"agent": "registration_agent"}
  event: tool_call            data: {"name": "validate_field"}
  event: delta                data: {"text": "...incremental..."}
  event: final                data: {"text": "...full...", "markers": {...}, "cost": {...}}

Stage order is contractual — the frontend renders chips per stage. Frame
buffer is `event:` + `data:` + `\n\n`; sse-starlette emits these as TEXT.

Bridge interface (stream_chat) is async-iterator-shaped so FastAPI's
EventSourceResponse can attach directly. Hermetic tests call it with a
fake runner; the live route uses the real ADK orchestrator.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Optional, Protocol

from agents.orchestrator import orchestrator
from schemas.session import SessionState
from tools import markers as marker_tools
from tools.cost_log import make_entry, write as write_cost
from tools.language import detect_language_rule
from tools.session import load_session, new_session_id, update_session

log = logging.getLogger(__name__)

_SPECIALIST_NAMES = {
    "registration_agent",
    "verification_agent",
    "booth_agent",
    "story_agent",
}


class _RunnerLike(Protocol):
    """Minimal contract the bridge needs from a Runner. Real ADK
    InMemoryRunner satisfies this; tests inject a stub."""

    async def run_async(  # type: ignore[empty-body]
        self, *, user_id: str, session_id: str, new_message: Any,
    ) -> AsyncIterator[Any]: ...


def _get_runner() -> _RunnerLike:
    """Lazy-create the ADK Runner. Imported at call time so unit tests
    can monkeypatch without paying the import cost."""
    from google.adk.runners import InMemoryRunner  # noqa: WPS433
    return InMemoryRunner(agent=orchestrator, app_name="sankalp")


_runner_factory = _get_runner


def set_runner_factory(factory) -> None:
    """Test-only: substitute a runner factory."""
    global _runner_factory
    _runner_factory = factory


def reset_runner_factory() -> None:
    global _runner_factory
    _runner_factory = _get_runner


def _ev(event: str, data: dict[str, Any]) -> dict[str, Any]:
    """sse-starlette dict shape: {event, data}. JSON-serialises data."""
    return {"event": event, "data": json.dumps(data, ensure_ascii=False, default=str)}


async def stream_chat(
    *,
    message: str,
    session_id: Optional[str] = None,
    language_override: Optional[str] = None,
    request_id: str = "no-id",
) -> AsyncIterator[dict[str, Any]]:
    """Drive the orchestrator and yield SSE-shaped events in stage order."""
    started = datetime.now(timezone.utc)
    sid = session_id or new_session_id()

    # 1. lang_detect — synchronous, emits in <50 ms so the frontend never
    #    sees a blank chat while we wait on Vertex AI to spin up.
    detected = language_override or detect_language_rule(message)
    yield _ev("lang_detect", {"language": detected, "session_id": sid})

    # 2. Persist language to SessionState for the prompts that read it.
    upd = update_session(sid, {"language": detected, "handoff_count": 0})
    state_dict = upd.get("state") if upd.get("ok") else load_session(sid).get("state", {})

    # 3. routing — placeholder until the orchestrator picks a sub-agent.
    yield _ev("routing", {"session_id": sid, "language": detected})

    # 4. Drive the orchestrator. ADK's Runner streams events; we translate.
    full_text_parts: list[str] = []
    tool_calls: list[str] = []
    last_author: Optional[str] = None
    tokens_in_total = 0
    tokens_out_total = 0
    last_intent: Optional[str] = None

    try:
        from google.genai import types as genai_types  # noqa: WPS433
        runner = _runner_factory()

        # Create / reuse an ADK session keyed by our session_id.
        # ADK's session_service is in-memory per-runner; we map our sid 1:1.
        adk_session = await runner.session_service.create_session(
            app_name="sankalp",
            user_id=sid,
            session_id=sid,
            state={"language_code": detected, **(state_dict or {})},
        )

        async for event in runner.run_async(
            user_id=sid,
            session_id=adk_session.id,
            new_message=genai_types.Content(role="user", parts=[genai_types.Part(text=message)]),
        ):
            author = getattr(event, "author", None)
            if author and author != last_author and author != "orchestrator":
                last_author = author
                last_intent = _agent_to_intent(author)
                yield _ev("specialist:" + author, {"agent": author, "intent": last_intent})

            content = getattr(event, "content", None)
            if content and getattr(content, "parts", None):
                for part in content.parts:
                    fc = getattr(part, "function_call", None)
                    if fc and getattr(fc, "name", None):
                        tool_calls.append(fc.name)
                        if fc.name in _SPECIALIST_NAMES:
                            # AgentTool dispatch — surface as routing transition.
                            last_author = fc.name
                            last_intent = _agent_to_intent(fc.name)
                            yield _ev(
                                "specialist:" + fc.name,
                                {"agent": fc.name, "intent": last_intent},
                            )
                        else:
                            yield _ev("tool_call", {"name": fc.name, "by": author or "orchestrator"})
                    text = getattr(part, "text", None)
                    if text:
                        full_text_parts.append(text)
                        if not _is_final(event):
                            yield _ev("delta", {"text": text, "author": author or "orchestrator"})

            usage = getattr(event, "usage_metadata", None)
            if usage is not None:
                tokens_in_total += getattr(usage, "prompt_token_count", 0) or 0
                tokens_out_total += getattr(usage, "candidates_token_count", 0) or 0

    except asyncio.CancelledError:
        log.info("client cancelled chat stream")
        raise
    except Exception as e:
        log.exception("stream_chat runner error")
        yield _ev("final", {
            "ok": False,
            "error": str(e),
            "user_message": "Something went wrong on my end — please try again.",
            "session_id": sid,
        })
        _persist_cost(
            request_id=request_id, session_id=sid, agent="orchestrator",
            model="gemini-2.5-flash", tokens_in=tokens_in_total, tokens_out=tokens_out_total,
            latency_ms=_ms_since(started), tool_calls=tool_calls,
            intent=last_intent, language=detected,
            ok_flag=False, error=str(e),
        )
        return

    # 5. final — full text + parsed structured markers.
    full_text = "".join(full_text_parts)
    parsed = _parse_markers(full_text)
    latency_ms = _ms_since(started)

    yield _ev("final", {
        "ok": True,
        "session_id": sid,
        "language": detected,
        "intent": last_intent,
        "text": marker_tools.strip_handoff(full_text),
        "markers": parsed,
        "tool_calls": tool_calls,
        "cost": {"tokens_in": tokens_in_total, "tokens_out": tokens_out_total, "latency_ms": latency_ms},
    })

    _persist_cost(
        request_id=request_id, session_id=sid, agent="orchestrator",
        model="gemini-2.5-flash", tokens_in=tokens_in_total, tokens_out=tokens_out_total,
        latency_ms=latency_ms, tool_calls=tool_calls,
        intent=last_intent, language=detected,
    )


def _agent_to_intent(author: str) -> Optional[str]:
    return {
        "registration_agent": "register",
        "verification_agent": "verify",
        "booth_agent": "booth",
        "story_agent": "story",
    }.get(author)


def _is_final(event: Any) -> bool:
    fn = getattr(event, "is_final_response", None)
    return bool(fn and fn())


def _ms_since(t0: datetime) -> int:
    return int((datetime.now(timezone.utc) - t0).total_seconds() * 1000)


def _parse_markers(text: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if (v := marker_tools.find_voter_record(text)) is not None:
        out["voter_record"] = v
    if (v := marker_tools.find_booth_card(text)) is not None:
        out["booth_card"] = v
    if (v := marker_tools.find_story(text)) is not None:
        out["story"] = v
    if (v := marker_tools.find_pdf_ready(text)) is not None:
        out["pdf_ready"] = v
    return out


def _persist_cost(**kwargs: Any) -> None:
    try:
        write_cost(make_entry(**kwargs))
    except Exception:
        log.exception("cost log write failed")
