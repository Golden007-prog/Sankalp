"""StoryAgent iteration sweep — 10 ACs, 5-axis rubric.

Invokes the live StoryAgent against the deployed Vertex AI for 10
constituencies, scores each on a 5-axis rubric, writes a JSON report at
`samples/story_iterations/run_{ts}.json`, and exits non-zero if any
narrative scores <20/25 on the auto-rubric.

Usage:
  python scripts/iterate_narratives.py [--lang en] [--out samples/story_iterations]

Cost: ~$0.05 per AC (Pro) → ~$0.50 per sweep. Cap iterations at 3 →
$1.50 of the $2.00 Phase-6 budget.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from agents.story import story_agent  # noqa: E402
from google.adk.runners import InMemoryRunner  # noqa: E402
from google.genai import types as genai_types  # noqa: E402
from tools.data_source import get_data_source  # noqa: E402

AC_SWEEP = [
    "KA-151",  # Bommanahalli (anchor)
    "BR-180",  # Patna Sahib (anchor)
    "TG-064",  # Goshamahal (anchor)
    "WB-159",  # Bhabanipur (anchor)
    "MH-176",  # Worli (anchor)
    "UP-173",  # Lucknow Central
    "TN-029",  # Velachery (Chennai)
    "GJ-039",  # Maninagar (Ahmedabad)
    "RJ-013",  # Sikar
    "KL-061",  # Thiruvananthapuram
]

BANNED_PHRASES = [
    r"\bin the heart of\b",
    r"\bnestled in\b",
    r"\btucked away\b",
    r"\bdid you know\b",
    r"\bit['']s worth noting\b",
    r"\binterestingly,\b",
    r"\bfurthermore\b",
    r"\bmoreover\b",
    r"\bin addition to that\b",
    r"\bmake sure to vote\b",
    r"\bdon['']t forget to vote\b",
    r"\bgo cast your\b",
]
BANNED_RE = re.compile("|".join(BANNED_PHRASES), re.IGNORECASE)
RHETORICAL_RE = re.compile(r"\?", re.MULTILINE)
EXCLAIM_RE = re.compile(r"!")


@dataclass
class Score:
    human_voice: int
    beat_structure: int
    real_numbers: int
    language_fidelity: int
    preachy_free: int

    def total(self) -> int:
        return (
            self.human_voice + self.beat_structure + self.real_numbers
            + self.language_fidelity + self.preachy_free
        )


def _word_count(text: str) -> int:
    return len([w for w in re.split(r"\s+", text) if w])


def score_narrative(text: str, ac_code: str, language: str) -> Score:
    src = get_data_source()
    c = src.get_constituency(ac_code)
    margins = [str(e.win_margin) for e in c.elections] if c else []
    margin_with_commas = [
        f"{m[:-3]},{m[-3:]}" if len(m) > 3 else m for m in margins
    ]

    # 1. Human voice — penalise banned phrases.
    banned_hits = len(BANNED_RE.findall(text))
    human_voice = max(1, 5 - banned_hits * 2)

    # 2. Beat structure — words split into thirds (paragraph-aware fallback).
    paragraphs = [p for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    if len(paragraphs) >= 3:
        wc = [_word_count(p) for p in paragraphs[:3]]
    else:
        words = [w for w in re.split(r"\s+", text) if w]
        third = max(1, len(words) // 3)
        wc = [
            _word_count(" ".join(words[:third])),
            _word_count(" ".join(words[third : 2 * third])),
            _word_count(" ".join(words[2 * third :])),
        ]
    target = (50, 100, 50)
    deltas = [abs(wc[i] - target[i]) / max(1, target[i]) for i in range(3)]
    avg_delta = sum(deltas) / 3
    if avg_delta < 0.25:
        beat_structure = 5
    elif avg_delta < 0.5:
        beat_structure = 4
    elif avg_delta < 0.8:
        beat_structure = 3
    else:
        beat_structure = 2

    # 3. Real numbers — at least 2 dataset margins must appear in text.
    margin_hits = sum(
        1 for m in margins + margin_with_commas if m and m in text
    )
    if margin_hits >= 2:
        real_numbers = 5
    elif margin_hits == 1:
        real_numbers = 3
    else:
        real_numbers = 1

    # 4. Language fidelity — if non-English language, expect script presence.
    if language == "en":
        # English narratives shouldn't carry stray Devanagari etc.
        non_latin = sum(1 for ch in text if ord(ch) > 0x0080 and ch.isalpha())
        language_fidelity = 5 if non_latin / max(1, len(text)) < 0.05 else 3
    else:
        non_latin = sum(1 for ch in text if ord(ch) > 0x0080 and ch.isalpha())
        ratio = non_latin / max(1, len([c for c in text if c.isalpha()]))
        language_fidelity = 5 if ratio > 0.5 else 2

    # 5. Preachy-free — no exclamations; cap rhetorical questions.
    bangs = len(EXCLAIM_RE.findall(text))
    qs = len(RHETORICAL_RE.findall(text))
    preachy_free = 5
    if bangs:
        preachy_free -= min(3, bangs)
    if qs > 1:  # one closing question is okay; more reads as rhetorical
        preachy_free -= min(2, qs - 1)
    preachy_free = max(1, preachy_free)

    return Score(human_voice, beat_structure, real_numbers, language_fidelity, preachy_free)


async def _generate_one(ac_code: str, language: str) -> dict[str, Any]:
    """Drive StoryAgent directly (skip the orchestrator) for fidelity."""
    runner = InMemoryRunner(agent=story_agent, app_name="sankalp-iter")
    sess = await runner.session_service.create_session(
        app_name="sankalp-iter", user_id="iter_user",
        state={"language_code": language},
    )

    # Collect every text fragment the agent emits — across multiple LLM
    # turns when it calls tools (get_constituency, store_story, etc.).
    # `is_final_response()` only fires for the very last event, which can
    # be a function_call dispatch with no text on it.
    text_parts: list[str] = []
    tokens_in = tokens_out = 0
    t0 = time.perf_counter()
    async for event in runner.run_async(
        user_id="iter_user", session_id=sess.id,
        new_message=genai_types.Content(
            role="user",
            parts=[genai_types.Part(text=f"Write the civic story for AC code {ac_code}. Respond in {language}.")],
        ),
    ):
        content = getattr(event, "content", None)
        if content and getattr(content, "parts", None):
            for p in content.parts:
                txt = getattr(p, "text", None)
                if txt and not getattr(p, "function_call", None):
                    text_parts.append(txt)
        usage = getattr(event, "usage_metadata", None)
        if usage:
            tokens_in += getattr(usage, "prompt_token_count", 0) or 0
            tokens_out += getattr(usage, "candidates_token_count", 0) or 0
    elapsed = time.perf_counter() - t0
    return {
        "ac_code": ac_code,
        "language": language,
        "text": "".join(text_parts),
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "elapsed_s": round(elapsed, 1),
    }


async def _main_async(args) -> int:
    if os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "").lower() != "true":
        print("ERROR: GOOGLE_GENAI_USE_VERTEXAI=true required.", file=sys.stderr)
        return 2

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path = out_dir / f"run_{ts}.json"

    results: list[dict[str, Any]] = []
    cum_tokens_in = cum_tokens_out = 0

    print(f"\nStoryAgent sweep — {len(AC_SWEEP)} ACs in {args.lang}\n")
    for ac in AC_SWEEP:
        print(f"  {ac:8s} ", end="", flush=True)
        try:
            row = await _generate_one(ac, args.lang)
        except Exception as e:
            print(f"ERROR  {e}")
            results.append({"ac_code": ac, "language": args.lang, "error": str(e)})
            continue
        s = score_narrative(row["text"], ac, args.lang)
        cum_tokens_in += row["tokens_in"]
        cum_tokens_out += row["tokens_out"]
        row.update({
            "scores": s.__dict__,
            "total": s.total(),
            "word_count": _word_count(row["text"]),
        })
        results.append(row)
        flag = "OK " if s.total() >= 20 else "LOW"
        print(
            f"{flag}  total={s.total():2d}/25  "
            f"hv={s.human_voice} bs={s.beat_structure} rn={s.real_numbers} "
            f"lf={s.language_fidelity} pf={s.preachy_free}  "
            f"words={row['word_count']:3d}  tokens={row['tokens_in']}/{row['tokens_out']}"
        )

    summary = {
        "ran_at": ts,
        "language": args.lang,
        "ac_count": len(AC_SWEEP),
        "results": results,
        "cumulative_tokens_in": cum_tokens_in,
        "cumulative_tokens_out": cum_tokens_out,
    }
    report_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nReport: {report_path}")

    bad = [r for r in results if r.get("total", 0) < 20]
    if bad:
        print(f"\n{len(bad)}/{len(AC_SWEEP)} narratives scored <20:")
        for r in bad:
            print(f"  {r['ac_code']}  total={r.get('total', 0)}")
        return 1
    print(f"\nAll {len(AC_SWEEP)} narratives ≥ 20/25.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", default="en", help="ISO code: en/hi/bn/ta/kn/te/mr")
    parser.add_argument("--out", default=str(ROOT / "samples" / "story_iterations"))
    args = parser.parse_args()
    return asyncio.run(_main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
