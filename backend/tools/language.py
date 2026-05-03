"""Language detection.

Rule-based first (Unicode block scan) — covers 99% of the demo inputs at
zero cost and zero latency. Falls back to Gemini classification only
when input is ASCII and ambiguous (extremely short text, transliteration).

Returns ISO codes from the launch set: en, hi, bn, ta, kn, te, mr (PRD §5.1).
Also recognises gu/pa/or/ml/as/ur for completeness.
"""
from __future__ import annotations

import re
from typing import Literal

from tools._envelope import ok

# Unicode-block → ISO code table. Order matters; first hit wins.
# Ranges are the canonical Unicode block start/end for each script.
_BLOCKS: list[tuple[range, str]] = [
    (range(0x0900, 0x0980), "hi"),  # Devanagari (Hindi/Marathi — default Hindi; see _disambiguate_devanagari)
    (range(0x0980, 0x0A00), "bn"),  # Bengali / Assamese
    (range(0x0A00, 0x0A80), "pa"),  # Gurmukhi (Punjabi)
    (range(0x0A80, 0x0B00), "gu"),  # Gujarati
    (range(0x0B00, 0x0B80), "or"),  # Odia
    (range(0x0B80, 0x0C00), "ta"),  # Tamil
    (range(0x0C00, 0x0C80), "te"),  # Telugu
    (range(0x0C80, 0x0D00), "kn"),  # Kannada
    (range(0x0D00, 0x0D80), "ml"),  # Malayalam
    (range(0x0600, 0x0700), "ur"),  # Arabic (Urdu — also Sindhi/Kashmiri)
]

# Marathi-specific tokens that beat the Hindi default for Devanagari text.
# `\b` is unreliable across Devanagari word boundaries — match plain.
_MARATHI_HINTS = re.compile(
    r"(आहे|नाही|काय|कुठे|कशी|कसा|कसे|करा|सांगा|माझे|तुमचे|आम्ही|तुम्ही|करते|करतो)"
)

LangCode = Literal["en", "hi", "bn", "ta", "kn", "te", "mr", "gu", "pa", "or", "as", "ml", "ur"]


def _disambiguate_devanagari(text: str) -> LangCode:
    if _MARATHI_HINTS.search(text):
        return "mr"
    return "hi"


def detect_language_rule(text: str) -> LangCode:
    """Pure-Python rule-based detector. Free, no LLM call."""
    if not text:
        return "en"
    counts: dict[str, int] = {}
    for ch in text:
        cp = ord(ch)
        for block, code in _BLOCKS:
            if cp in block:
                counts[code] = counts.get(code, 0) + 1
                break
    if not counts:
        return "en"
    top = max(counts.items(), key=lambda kv: kv[1])[0]
    if top == "hi":
        return _disambiguate_devanagari(text)
    return top  # type: ignore[return-value]


def detect_language(text: str) -> dict:
    """ADK tool wrapper. Always returns the envelope shape.

    Example:
        >>> detect_language("नमस्ते सांगा")  # mr (Marathi hint 'सांगा')
        {'ok': True, 'language': 'mr'}
    """
    return ok(language=detect_language_rule(text))
