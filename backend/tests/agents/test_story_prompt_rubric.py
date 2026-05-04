"""Pure-Python tests for the rubric scorer used by scripts/iterate_narratives.py.

Auto-graders the live test relies on. These run hermetic — no LLM calls.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from iterate_narratives import score_narrative  # type: ignore[import-not-found]


KA_151_GOOD = """\
Bommanahalli runs along the long shadow of Silk Board Junction —
a mile of tech parks, a lake that's seen three names in twenty years,
and a population that doubled while the BBMP map stayed the same.
It has voted both ways since the constituency was carved out in 2008.

In 2023, 4,218 votes decided which way Bommanahalli leaned. That is
fewer people than ride a single BMTC volvo at 9 a.m. on Hosur Road.
Fewer than the queue outside Brand Factory on a sale Saturday.
In 2018, the gap was 23,218. In 2013, 12,011. Each cycle, the margin
has gotten thinner — and turnout has stayed under 54%.

4,218 is the number to remember. Three apartments in BTM Layout. A
Sunday crowd at Madiwala Lake. If 4,218 votes decided it last time,
your one vote and two friends' could change the next.
"""

KA_151_BAD_PREACHY = """\
In the heart of Bengaluru lies Bommanahalli! Did you know that this
constituency has a thrilling history? Furthermore, it's a place where
every vote counts! Make sure to vote — democracy needs YOU!
"""


def test_good_narrative_scores_high() -> None:
    s = score_narrative(KA_151_GOOD, "KA-151", "en")
    assert s.total() >= 20, f"good narrative scored {s.total()}: {s.__dict__}"
    assert s.human_voice == 5
    assert s.preachy_free == 5


def test_bad_narrative_scores_low() -> None:
    s = score_narrative(KA_151_BAD_PREACHY, "KA-151", "en")
    assert s.total() < 15, f"preachy narrative scored too high: {s.__dict__}"
    assert s.human_voice <= 2
    assert s.preachy_free <= 2


def test_non_english_language_penalised_for_latin_only_text() -> None:
    s = score_narrative(KA_151_GOOD, "KA-151", "hi")
    assert s.language_fidelity <= 2  # English text rated for Hindi → mismatch
