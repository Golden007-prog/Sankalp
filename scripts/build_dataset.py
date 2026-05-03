"""Build Sankalp's mock electoral dataset.

Reads scripts/inputs/ac_master.csv and produces three JSON files under
backend/data/:

  constituencies.json   — 100 ACs with 5 elections of history each
  electoral_roll.json   — ~5,000 synthetic voter records (Faker, seed=42)
  booths.json           — booth metadata referenced by the synthetic roll

Idempotent: re-running with the same inputs produces byte-identical output.

Per docs/DATA.md every voter has is_synthetic=True; every accessibility
block has synthetic=True; every election has a `source` and is flagged
`is_synthetic_election` with a `synthesis_note` until cross-checked
against the cited ECI Statistical Report.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from faker import Faker

# Make backend.schemas importable without installing the package.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from schemas.electoral import (  # noqa: E402
    AccessibilityFlags,
    Address,
    Booth,
    Constituency,
    Demographics,
    DemoPersona,
    ElectionRecord,
    Provenance,
    VoterRecord,
)

SEED = 42
SYNTHESIS_NOTE = (
    "Headline values seeded from publicly reported election outcomes; "
    "exact margins/turnout pending verification against the cited ECI "
    "Statistical Report. Flag flips to is_synthetic_election=False when "
    "a record is hand-checked. See docs/DATA.md §1, §5."
)
ANCHOR_SOURCE_TPL = "ECI Statistical Report {state} {year}, AC {ac_code}"
DEFAULT_LANG_BY_STATE: dict[str, list[str]] = {
    "AN": ["hi", "ta"], "AP": ["te"], "AR": ["en", "hi"], "AS": ["as"],
    "BR": ["hi"], "CG": ["hi"], "CH": ["hi", "pa"], "DH": ["gu", "hi"],
    "DL": ["hi", "pa", "ur"], "GA": ["en"], "GJ": ["gu"], "HP": ["hi"],
    "HR": ["hi"], "JH": ["hi"], "JK": ["ur", "hi"], "KA": ["kn"],
    "KL": ["ml"], "LA": ["en", "hi"], "LD": ["ml"], "MH": ["mr"],
    "ML": ["en"], "MN": ["en", "bn"], "MP": ["hi"], "MZ": ["en"],
    "NL": ["en"], "OR": ["or"], "PB": ["pa"], "PY": ["ta", "en"],
    "RJ": ["hi"], "SK": ["en", "hi"], "TG": ["te", "ur"], "TN": ["ta"],
    "TR": ["bn"], "UK": ["hi"], "UP": ["hi", "ur"], "WB": ["bn"],
}
PARTY_POOLS = {
    "BR": ["BJP", "RJD", "JDU", "INC"],
    "TG": ["BRS", "INC", "BJP", "AIMIM"],
    "WB": ["TMC", "BJP", "INC"],
    "MH": ["BJP", "SHS", "NCP", "INC"],
    "TN": ["DMK", "AIADMK", "BJP", "INC"],
    "KA": ["BJP", "INC", "JDS"],
    "UP": ["BJP", "SP", "BSP", "INC"],
    "KL": ["CPI(M)", "INC", "IUML", "BJP"],
    "PB": ["AAP", "INC", "SAD", "BJP"],
    "DL": ["AAP", "BJP", "INC"],
    "GJ": ["BJP", "INC", "AAP"],
    "AP": ["YSRCP", "TDP", "BJP", "JSP"],
    "OR": ["BJD", "BJP", "INC"],
    "JK": ["JKNC", "PDP", "INC", "BJP"],
}
DEFAULT_PARTIES = ["BJP", "INC", "AAP", "Independent"]

# 5 anchor ACs with publicly-known headline results. Per docs/DATA.md,
# these are still flagged is_synthetic_election=True until cross-checked
# against ECI's published Statistical Reports — the synthesis_note explains.
# Year/type/winner_party are accurate to the best of training data;
# margin/turnout/votes are plausible-but-unverified.
ANCHOR_ELECTIONS: dict[str, list[dict[str, Any]]] = {
    "KA-151": [  # Bommanahalli — Riya
        {"year": 2023, "type": "Vidhan Sabha", "winner_party": "INC",
         "runner_up_party": "BJP", "win_margin": 8453, "turnout_pct": 53.2},
        {"year": 2018, "type": "Vidhan Sabha", "winner_party": "BJP",
         "runner_up_party": "INC", "win_margin": 23218, "turnout_pct": 50.7},
        {"year": 2013, "type": "Vidhan Sabha", "winner_party": "BJP",
         "runner_up_party": "INC", "win_margin": 12011, "turnout_pct": 47.4},
        {"year": 2008, "type": "Vidhan Sabha", "winner_party": "BJP",
         "runner_up_party": "INC", "win_margin": 5811, "turnout_pct": 49.0},
        {"year": 2004, "type": "Vidhan Sabha", "winner_party": "INC",
         "runner_up_party": "BJP", "win_margin": 4218, "turnout_pct": 46.1},
    ],
    "BR-180": [  # Patna Sahib — Ravi
        {"year": 2020, "type": "Vidhan Sabha", "winner_party": "BJP",
         "runner_up_party": "INC", "win_margin": 33108, "turnout_pct": 49.2},
        {"year": 2015, "type": "Vidhan Sabha", "winner_party": "BJP",
         "runner_up_party": "INC", "win_margin": 25218, "turnout_pct": 51.4},
        {"year": 2010, "type": "Vidhan Sabha", "winner_party": "BJP",
         "runner_up_party": "INC", "win_margin": 28311, "turnout_pct": 48.7},
        {"year": 2005, "type": "Vidhan Sabha", "winner_party": "BJP",
         "runner_up_party": "INC", "win_margin": 19228, "turnout_pct": 45.8},
        {"year": 2000, "type": "Vidhan Sabha", "winner_party": "BJP",
         "runner_up_party": "RJD", "win_margin": 12018, "turnout_pct": 43.2},
    ],
    "TG-064": [  # Goshamahal — Priya
        {"year": 2023, "type": "Vidhan Sabha", "winner_party": "BJP",
         "runner_up_party": "BRS", "win_margin": 8211, "turnout_pct": 56.1},
        {"year": 2018, "type": "Vidhan Sabha", "winner_party": "BJP",
         "runner_up_party": "TRS", "win_margin": 17819, "turnout_pct": 54.3},
        {"year": 2014, "type": "Vidhan Sabha", "winner_party": "BJP",
         "runner_up_party": "AIMIM", "win_margin": 12821, "turnout_pct": 52.7},
        {"year": 2009, "type": "Vidhan Sabha", "winner_party": "INC",
         "runner_up_party": "TRS", "win_margin": 6918, "turnout_pct": 49.4},
        {"year": 2004, "type": "Vidhan Sabha", "winner_party": "INC",
         "runner_up_party": "TDP", "win_margin": 4521, "turnout_pct": 47.0},
    ],
    "WB-159": [  # Bhabanipur
        {"year": 2021, "type": "Vidhan Sabha", "winner_party": "TMC",
         "runner_up_party": "BJP", "win_margin": 58835, "turnout_pct": 57.0},
        {"year": 2016, "type": "Vidhan Sabha", "winner_party": "TMC",
         "runner_up_party": "INC", "win_margin": 25301, "turnout_pct": 60.2},
        {"year": 2011, "type": "Vidhan Sabha", "winner_party": "TMC",
         "runner_up_party": "CPI(M)", "win_margin": 30518, "turnout_pct": 64.5},
        {"year": 2006, "type": "Vidhan Sabha", "winner_party": "CPI(M)",
         "runner_up_party": "TMC", "win_margin": 12211, "turnout_pct": 71.8},
        {"year": 2001, "type": "Vidhan Sabha", "winner_party": "CPI(M)",
         "runner_up_party": "TMC", "win_margin": 8920, "turnout_pct": 69.4},
    ],
    "MH-176": [  # Worli
        {"year": 2019, "type": "Vidhan Sabha", "winner_party": "SHS",
         "runner_up_party": "NCP", "win_margin": 67427, "turnout_pct": 51.4},
        {"year": 2014, "type": "Vidhan Sabha", "winner_party": "SHS",
         "runner_up_party": "BJP", "win_margin": 18219, "turnout_pct": 49.8},
        {"year": 2009, "type": "Vidhan Sabha", "winner_party": "NCP",
         "runner_up_party": "SHS", "win_margin": 4218, "turnout_pct": 46.1},
        {"year": 2004, "type": "Vidhan Sabha", "winner_party": "SHS",
         "runner_up_party": "NCP", "win_margin": 11020, "turnout_pct": 45.5},
        {"year": 1999, "type": "Vidhan Sabha", "winner_party": "SHS",
         "runner_up_party": "INC", "win_margin": 7019, "turnout_pct": 44.0},
    ],
}

# Demo personas baked into the synthetic roll so smoke tests find them.
DEMO_PERSONAS: list[dict[str, Any]] = [
    {
        "persona_id": "riya",
        "epic_number": "ABC1234567",
        "name": "Riya Sharma",
        "name_native": "रिया शर्मा",
        "dob": "2007-04-12",
        "gender": "F",
        "relation_type": "father",
        "relation_name": "Rajesh Sharma",
        "address": {
            "house": "42", "street": "MG Road", "locality": "Bommanahalli",
            "city": "Bengaluru", "state": "KA", "pincode": "560068",
        },
        "ac_code": "KA-151", "booth_id": "KA-151_001",
        "journey": "verify_happy",
        "notes": "First-time voter, Bommanahalli. PRD §2.1.",
    },
    {
        "persona_id": "ravi",
        "epic_number": "BIH7821093",
        "name": "Ravi Kumar",
        "name_native": "रवि कुमार",
        "dob": "1962-11-08",
        "gender": "M",
        "relation_type": "father",
        "relation_name": "Shyam Kumar",
        "address": {
            "house": "12", "street": "Old Bypass", "locality": "Kankarbagh",
            "city": "Patna", "state": "BR", "pincode": "800020",
        },
        "ac_code": "BR-180", "booth_id": "BR-180_001",
        "journey": "form8_address",
        "notes": "62yo with outdated 1998 EPIC, address change scenario. PRD §2.2.",
    },
    {
        "persona_id": "priya",
        "epic_number": "TGS9912204",
        "name": "Priya Reddy",
        "name_native": "ప్రియ రెడ్డి",
        "dob": "1996-03-21",
        "gender": "F",
        "relation_type": "father",
        "relation_name": "Suresh Reddy",
        "address": {
            "house": "204-A", "street": "SR Nagar Main Road", "locality": "Goshamahal",
            "city": "Hyderabad", "state": "TG", "pincode": "500001",
        },
        "ac_code": "TG-064", "booth_id": "TG-064_001",
        "journey": "story",
        "notes": "Tech-confident voter, story share path. PRD §2.3.",
    },
    {
        "persona_id": "dedup_a",
        "epic_number": "DUP1112223",
        "name": "Anjali Verma",
        "name_native": "अंजली वर्मा",
        "dob": "1990-06-15",
        "gender": "F",
        "relation_type": "father",
        "relation_name": "Manoj Verma",
        "address": {
            "house": "78", "street": "Park Street", "locality": "Lucknow Central",
            "city": "Lucknow", "state": "UP", "pincode": "226001",
        },
        "ac_code": "UP-173", "booth_id": "UP-173_001",
        "journey": "dedup",
        "notes": "Duplicate-registration test, paired with dedup_b. AGENTS.md §3.",
    },
    {
        "persona_id": "dedup_b",
        "epic_number": "DUP4445556",
        "name": "Anjali Verma",
        "name_native": "अंजली वर्मा",
        "dob": "1990-06-15",
        "gender": "F",
        "relation_type": "father",
        "relation_name": "Manoj Verma",
        "address": {
            "house": "203", "street": "Sapru Marg", "locality": "Hazratganj",
            "city": "Lucknow", "state": "UP", "pincode": "226001",
        },
        "ac_code": "UP-174", "booth_id": "UP-174_001",
        "journey": "dedup",
        "notes": "Duplicate-registration test, paired with dedup_a.",
    },
]


@dataclass(frozen=True)
class AcRow:
    ac_code: str
    ac_name: str
    ac_name_native: str | None
    state: str
    state_name: str
    district: str
    lok_sabha_code: str | None
    lok_sabha_name: str | None
    type: str
    total_electors: int
    male_electors: int
    female_electors: int
    total_booths: int
    centroid_lat: float
    centroid_lng: float


def load_ac_master(path: Path) -> list[AcRow]:
    rows: list[AcRow] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(
                AcRow(
                    ac_code=r["ac_code"].strip(),
                    ac_name=r["ac_name"].strip(),
                    ac_name_native=(r["ac_name_native"].strip() or None),
                    state=r["state"].strip(),
                    state_name=r["state_name"].strip(),
                    district=r["district"].strip(),
                    lok_sabha_code=(r["lok_sabha_code"].strip() or None),
                    lok_sabha_name=(r["lok_sabha_name"].strip() or None),
                    type=r["type"].strip(),
                    total_electors=int(r["total_electors"]),
                    male_electors=int(r["male_electors"]),
                    female_electors=int(r["female_electors"]),
                    total_booths=int(r["total_booths"]),
                    centroid_lat=float(r["centroid_lat"]),
                    centroid_lng=float(r["centroid_lng"]),
                )
            )
    if len(rows) != 100:
        raise SystemExit(f"ac_master.csv must have 100 rows, found {len(rows)}")
    return rows


def synthesize_elections(ac: AcRow, rng: random.Random) -> list[ElectionRecord]:
    """Five plausible Vidhan Sabha elections, year-descending. All flagged
    is_synthetic_election=True per docs/DATA.md §1 (until cross-checked)."""
    if ac.ac_code in ANCHOR_ELECTIONS:
        anchor_data = ANCHOR_ELECTIONS[ac.ac_code]
        records: list[ElectionRecord] = []
        for e in anchor_data:
            polled = int(ac.total_electors * (e["turnout_pct"] / 100))
            records.append(
                ElectionRecord(
                    year=e["year"],
                    type=e["type"],
                    winner_party=e["winner_party"],
                    runner_up_party=e["runner_up_party"],
                    win_margin=e["win_margin"],
                    turnout_pct=e["turnout_pct"],
                    total_votes_polled=polled,
                    source=ANCHOR_SOURCE_TPL.format(
                        state=ac.state_name, year=e["year"], ac_code=ac.ac_code
                    ),
                    is_synthetic_election=True,
                    synthesis_note=SYNTHESIS_NOTE,
                )
            )
        return records

    parties = PARTY_POOLS.get(ac.state, DEFAULT_PARTIES)
    base_year = 2024 if rng.random() < 0.5 else 2023
    election_years = [base_year, base_year - 5, base_year - 10, base_year - 15, base_year - 20]
    records = []
    for year in election_years:
        winner = rng.choice(parties)
        runner_pool = [p for p in parties if p != winner]
        runner = rng.choice(runner_pool) if runner_pool else "Independent"
        turnout = round(rng.uniform(45.0, 72.0), 1)
        polled = int(ac.total_electors * (turnout / 100))
        margin = max(800, int(polled * rng.uniform(0.005, 0.18)))
        records.append(
            ElectionRecord(
                year=year, type="Vidhan Sabha",
                winner_party=winner, runner_up_party=runner,
                win_margin=margin, turnout_pct=turnout,
                total_votes_polled=polled,
                source=f"Synthesis vSANK-1 (state={ac.state}, ac={ac.ac_code})",
                is_synthetic_election=True,
                synthesis_note=SYNTHESIS_NOTE,
            )
        )
    return records


def synthesize_demographics(ac: AcRow, rng: random.Random) -> Demographics:
    langs = DEFAULT_LANG_BY_STATE.get(ac.state, ["hi", "en"])
    is_urban_seat = "City" in ac.ac_name or "Urban" in ac.district or "Mumbai" in ac.ac_name
    return Demographics(
        literacy_pct=round(rng.uniform(72.0, 91.0), 1),
        urban_pct=round(rng.uniform(85.0, 100.0) if is_urban_seat else rng.uniform(20.0, 80.0), 1),
        primary_languages=langs,  # type: ignore[arg-type]
        is_synthetic=True,
        source="Synthesis vSANK-1; cross-check against Census 2011 + ECI Atlas",
    )


def landmarks_for(ac: AcRow) -> list[str]:
    """A few generic-but-plausible landmarks per AC. Real names where they
    are well-known; 'Local Market', 'District Hospital' otherwise."""
    well_known: dict[str, list[str]] = {
        "KA-151": ["BTM Layout", "Silk Board Junction", "Madiwala Lake"],
        "BR-180": ["Gandhi Maidan", "Patna Junction", "Patna High Court"],
        "TG-064": ["Charminar (nearby)", "Imlibun Bus Stand", "Begum Bazaar"],
        "WB-159": ["Maidan", "Forum Mall", "Rabindra Sadan Metro"],
        "MH-176": ["Worli Sea Face", "Nehru Planetarium", "Haji Ali"],
    }
    if ac.ac_code in well_known:
        return well_known[ac.ac_code]
    return [f"{ac.ac_name} Market", f"{ac.district} District Office", "Local Bus Stand"]


def build_constituencies(rows: list[AcRow], rng: random.Random) -> list[Constituency]:
    out: list[Constituency] = []
    for ac in rows:
        elections = synthesize_elections(ac, rng)
        demos = synthesize_demographics(ac, rng)
        prov = Provenance(
            name_and_codes="ECI Atlas of Indian Elections; Delimitation Commission Order 2008",
            elections="Per-record; see ElectionRecord.source. v0 dataset is fully synthesized; flip is_synthetic_election=False after ECI Statistical Report verification.",
            demographics=demos.source,
            booths="State CEO website naming patterns; addresses synthesized for demo (see booths.json).",
            notes="Synthetic dataset for hackathon demo. See docs/DATA.md.",
        )
        out.append(
            Constituency(
                ac_code=ac.ac_code, ac_name=ac.ac_name, ac_name_native=ac.ac_name_native,
                state=ac.state,  # type: ignore[arg-type]
                state_name=ac.state_name, district=ac.district,
                lok_sabha_code=ac.lok_sabha_code, lok_sabha_name=ac.lok_sabha_name,
                type=ac.type,  # type: ignore[arg-type]
                total_electors=ac.total_electors, male_electors=ac.male_electors,
                female_electors=ac.female_electors,
                third_gender_electors=max(0, ac.total_electors - ac.male_electors - ac.female_electors),
                total_booths=ac.total_booths,
                centroid_lat=ac.centroid_lat, centroid_lng=ac.centroid_lng,
                elections=elections, demographics=demos,
                key_landmarks=landmarks_for(ac), provenance=prov,
            )
        )
    return out


def epic_for_state(state: str, n: int) -> str:
    """3-letter state-derived prefix + 7 digits, format-valid per ECI."""
    letters = (state + "X")[:3]
    return f"{letters[0]}{letters[1] if len(letters) > 1 else 'X'}{letters[2] if len(letters) > 2 else 'X'}{n:07d}"


def build_booths(constituencies: list[Constituency], rng: random.Random) -> list[Booth]:
    """~5 booths per AC, named with real schoolish patterns. Synthetic
    accessibility data per docs/DATA.md §4."""
    out: list[Booth] = []
    booth_name_patterns = [
        "Government Higher Primary School, {locality}",
        "Government High School, {locality}",
        "Municipal Corporation School, {locality}",
        "Zilla Parishad School, {locality}",
        "Community Hall, {locality}",
    ]
    for c in constituencies:
        per_ac = max(5, min(8, c.total_booths // 60))
        for i in range(per_ac):
            booth_id = f"{c.ac_code}_{i+1:03d}"
            pattern = rng.choice(booth_name_patterns)
            locality_hint = c.ac_name
            name = pattern.format(locality=locality_hint)
            address = f"{rng.randint(1, 200)}, {locality_hint} Main Road, {c.district}, {c.state_name}"
            jitter_lat = c.centroid_lat + rng.uniform(-0.02, 0.02)
            jitter_lng = c.centroid_lng + rng.uniform(-0.02, 0.02)
            access = AccessibilityFlags(
                wheelchair=rng.random() < 0.62,
                ramp=rng.random() < 0.71,
                ground_floor=rng.random() < 0.83,
                language_assistance=DEFAULT_LANG_BY_STATE.get(c.state, ["hi", "en"]),  # type: ignore[arg-type]
                sign_language=rng.random() < 0.18,
                braille_ballot=rng.random() < 0.07,
            )
            out.append(
                Booth(
                    booth_id=booth_id, ac_code=c.ac_code,
                    name=name, address=address,
                    lat=round(jitter_lat, 6), lng=round(jitter_lng, 6),
                    accessibility=access,
                    source=f"State CEO {c.state_name} (synthesized addresses; see docs/DATA.md §4)",
                )
            )
    return out


def build_voter_roll(
    constituencies: list[Constituency],
    booths: list[Booth],
    target_size: int,
) -> tuple[list[VoterRecord], list[DemoPersona]]:
    fake = Faker("en_IN")
    Faker.seed(SEED)
    rng = random.Random(SEED + 1)

    by_ac_booths: dict[str, list[str]] = {}
    for b in booths:
        by_ac_booths.setdefault(b.ac_code, []).append(b.booth_id)
    ac_index: dict[str, Constituency] = {c.ac_code: c for c in constituencies}

    # Materialise demo personas first so smoke tests are deterministic.
    voters: list[VoterRecord] = []
    personas: list[DemoPersona] = []
    seen_epics: set[str] = set()
    for p in DEMO_PERSONAS:
        addr = Address(**p["address"])  # type: ignore[arg-type]
        v = VoterRecord(
            epic_number=p["epic_number"],
            name=p["name"], name_native=p["name_native"],
            dob=date.fromisoformat(p["dob"]),
            gender=p["gender"], relation_type=p["relation_type"],
            relation_name=p["relation_name"], address=addr,
            ac_code=p["ac_code"], booth_id=p["booth_id"],
        )
        voters.append(v); seen_epics.add(v.epic_number)
        personas.append(
            DemoPersona(
                persona_id=p["persona_id"], epic_number=p["epic_number"],
                name=p["name"], journey=p["journey"], notes=p["notes"],
            )
        )

    # Synthetic remainder, distributed proportionally to AC elector count.
    weights = [c.total_electors for c in constituencies]
    today = date(2026, 1, 1)
    while len(voters) < target_size:
        c = rng.choices(constituencies, weights=weights, k=1)[0]
        booth_pool = by_ac_booths.get(c.ac_code, [])
        if not booth_pool:
            continue
        gender = rng.choices(["M", "F", "T"], weights=[51, 48, 1], k=1)[0]
        first = fake.first_name_male() if gender == "M" else fake.first_name_female()
        last = fake.last_name()
        full = f"{first} {last}"
        n = len(voters) + 1
        epic = epic_for_state(c.state, n)
        if epic in seen_epics:
            continue
        seen_epics.add(epic)
        age = rng.randint(18, 92)
        dob_val = today - timedelta(days=age * 365 + rng.randint(0, 364))
        relation_t = rng.choice(["father", "mother", "husband", "wife"])
        relation_n = f"{fake.first_name()} {last}"
        addr = Address(
            house=str(rng.randint(1, 990)),
            street=fake.street_name(),
            locality=c.ac_name,
            city=c.district,
            state=c.state,  # type: ignore[arg-type]
            pincode=fake.postcode().replace(" ", "")[:6].zfill(6),
        )
        voters.append(
            VoterRecord(
                epic_number=epic, name=full, name_native=None,
                dob=dob_val, gender=gender,  # type: ignore[arg-type]
                relation_type=relation_t,  # type: ignore[arg-type]
                relation_name=relation_n, address=addr,
                ac_code=c.ac_code, booth_id=rng.choice(booth_pool),
            )
        )
    voters.sort(key=lambda v: v.epic_number)
    return voters, personas


def cross_reference(constituencies: list[Constituency], voters: list[VoterRecord], booths: list[Booth]) -> None:
    ac_codes = {c.ac_code for c in constituencies}
    booth_ids = {b.booth_id for b in booths}
    for v in voters:
        if v.ac_code not in ac_codes:
            raise ValueError(f"voter {v.epic_number} ac_code {v.ac_code} not in constituencies")
        if v.booth_id not in booth_ids:
            raise ValueError(f"voter {v.epic_number} booth_id {v.booth_id} not in booths")
    for b in booths:
        if b.ac_code not in ac_codes:
            raise ValueError(f"booth {b.booth_id} ac_code {b.ac_code} not in constituencies")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"), default=_default, sort_keys=False)
        f.write("\n")


def _default(o: Any) -> Any:
    if isinstance(o, date):
        return o.isoformat()
    raise TypeError(f"unserialisable: {type(o).__name__}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", default=str(ROOT / "scripts" / "inputs"))
    parser.add_argument("--out", default=str(ROOT / "backend" / "data"))
    parser.add_argument("--voters", type=int, default=4500)
    args = parser.parse_args()

    inputs = Path(args.inputs)
    out = Path(args.out)
    rng = random.Random(SEED)

    rows = load_ac_master(inputs / "ac_master.csv")
    constituencies = build_constituencies(rows, rng)
    booths = build_booths(constituencies, rng)
    voters, personas = build_voter_roll(constituencies, booths, target_size=args.voters)
    cross_reference(constituencies, voters, booths)

    write_json(
        out / "constituencies.json",
        [c.model_dump(mode="json", exclude_none=True) for c in constituencies],
    )
    write_json(
        out / "electoral_roll.json",
        [v.model_dump(mode="json", exclude_none=True) for v in voters],
    )
    write_json(
        out / "booths.json",
        [b.model_dump(mode="json", exclude_none=True) for b in booths],
    )
    write_json(
        out / "demo_personas.json",
        [p.model_dump(mode="json", exclude_none=True) for p in personas],
    )

    sizes = {
        "constituencies.json": (out / "constituencies.json").stat().st_size,
        "electoral_roll.json": (out / "electoral_roll.json").stat().st_size,
        "booths.json": (out / "booths.json").stat().st_size,
        "demo_personas.json": (out / "demo_personas.json").stat().st_size,
    }
    total = sum(sizes.values())
    for k, v in sizes.items():
        print(f"  {k:24s} {v/1024:8.1f} KiB")
    print(f"  {'total':24s} {total/1024:8.1f} KiB ({total/1024/1024:.2f} MiB)")
    print(f"  voters={len(voters)} constituencies={len(constituencies)} booths={len(booths)} personas={len(personas)}")
    if total > 2 * 1024 * 1024:
        print("WARNING: total exceeds 2 MiB target from docs/DATA.md §1.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
