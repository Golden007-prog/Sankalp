"""PII redaction for the root logger.

Applies to every log line emitted by Sankalp. Scrubs known-PII fields
from log records (both the message string and any structured `extra`
dict). Per ARCHITECTURE.md §10 / §11.
"""
from __future__ import annotations

import logging
import re

# Field names that may contain real PII per docs/ARCHITECTURE.md §10.
_PII_KEYS = {
    "name", "full_name", "name_native", "full_name_native",
    "address", "house", "street", "locality", "city",
    "epic_number", "epic", "dob", "mobile", "email",
    "relation_name",
}

# Inline patterns we strip from free-text log messages.
_EPIC_RE = re.compile(r"\b[A-Z]{3}\d{7}\b")
# Indian mobile: optional +91 + 10 digits, or 10-digit starting 6-9.
_MOBILE_RE = re.compile(r"(?:\+91[\s-]?)?[6-9]\d{9}")
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_PIN_RE = re.compile(r"\b\d{6}\b")  # PIN codes are not strictly PII but worth masking.

REDACTED = "[REDACTED]"


def redact_text(s: str) -> str:
    """Public — strip EPIC/email/mobile/etc. patterns from a free-text string."""
    if not isinstance(s, str):
        return s
    s = _EPIC_RE.sub(REDACTED, s)
    s = _EMAIL_RE.sub(REDACTED, s)
    s = _MOBILE_RE.sub(REDACTED, s)
    return s


# Backwards-compat alias.
_redact_text = redact_text


class PiiRedactor(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003
        # Scrub the formatted message.
        try:
            if isinstance(record.msg, str):
                record.msg = _redact_text(record.msg)
            if record.args:
                # Tuple of args used by old-style formatting.
                record.args = tuple(
                    _redact_text(a) if isinstance(a, str) else a for a in record.args
                )
        except Exception:
            pass

        # Scrub any structured `extra` keys we know carry PII.
        for k in list(getattr(record, "__dict__", {}).keys()):
            if k in _PII_KEYS:
                setattr(record, k, REDACTED)
        return True


def install() -> None:
    """Attach the redactor once to the root logger so every handler sees it."""
    root = logging.getLogger()
    if any(isinstance(f, PiiRedactor) for f in root.filters):
        return
    root.addFilter(PiiRedactor())
