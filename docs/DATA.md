# Data

How Sankalp gets, structures, and discloses electoral data. The single most important section to get right for trust and rubric.

---

## 1. The honest truth about ECI data

`voters.eci.gov.in` is the consumer-facing portal for the Election Commission of India. It does not expose a public API. Programmatic access requires either:

- **Scraping**, which is rate-limited, fragile, and arguably violates the portal's Terms of Service.
- **Official partnership**, which is a months-long process unsuitable for a hackathon.

Sankalp does neither. Instead, it ships with a curated dataset built from sources that are explicitly published for public use: the Election Commission's *Statistical Reports*, gazetted constituency boundary notifications, and the *Atlas of Indian Elections*. This is real data, sourced legally, and disclosed clearly.

The result is a demo that walks 100 representative constituencies end-to-end with credible historical numbers, while leaving a clean integration seam for any future partner with real-time access.

## 2. What's in the dataset

Three JSON files live under `backend/data/`. Total size: under 2 MB compressed.

### 2.1 `constituencies.json`

100 representative constituencies covering all major states. Each entry:

```json
{
  "ac_code": "151",
  "ac_name": "Bommanahalli",
  "ac_name_native": "ಬೊಮ್ಮನಹಳ್ಳಿ",
  "state": "Karnataka",
  "state_code": "KA",
  "district": "Bengaluru Urban",
  "lok_sabha_code": "S10",
  "lok_sabha_name": "Bangalore South",
  "type": "GEN",
  "total_electors": 487523,
  "male_electors": 254182,
  "female_electors": 233311,
  "third_gender_electors": 30,
  "total_booths": 412,
  "centroid": {"lat": 12.9019, "lng": 77.6206},
  "boundary_polygon_url": "https://...geojson",
  "elections": [
    {
      "year": 2023,
      "type": "Vidhan Sabha",
      "winner_party": "INC",
      "runner_up_party": "BJP",
      "win_margin": 8453,
      "turnout_pct": 53.2,
      "total_votes_polled": 259364,
      "source": "ECI Statistical Report Karnataka 2023, Table 8"
    },
    { "year": 2018, "...": "..." },
    { "year": 2013, "...": "..." },
    { "year": 2008, "...": "..." },
    { "year": 2004, "...": "..." }
  ],
  "demographics": {
    "literacy_pct": 78.4,
    "urban_pct": 100,
    "primary_languages": ["Kannada", "Tamil", "Telugu", "Hindi"]
  },
  "key_landmarks": ["BTM Layout", "Silk Board Junction", "Madiwala Lake"]
}
```

The `source` field is required for every election record. If we don't have a source, the record doesn't exist.

### 2.2 `electoral_roll.json`

~5,000 synthetic voter records distributed across the 100 constituencies. Each entry:

```json
{
  "epic_number": "ABC1234567",
  "name": "Riya Sharma",
  "name_native": "रिया शर्मा",
  "dob": "2007-04-12",
  "gender": "F",
  "relation_type": "father",
  "relation_name": "Rajesh Sharma",
  "address": {
    "house": "42",
    "street": "MG Road",
    "locality": "Bommanahalli",
    "city": "Bengaluru",
    "state": "Karnataka",
    "pincode": "560068"
  },
  "ac_code": "151",
  "booth_id": "151_217",
  "is_synthetic": true
}
```

Every record has `is_synthetic: true`. The names are generated; addresses use real PIN codes and real localities but invented house numbers.

The dataset is built to surface specific demo cases:

- A first-time voter (Riya) successfully on the roll
- A senior voter (Ravi) with an outdated address
- A duplicate registration case (same name + DOB across two ACs)
- A name-only search returning multiple matches

These are scripted into `backend/data/demo_personas.json` so the smoke test can hit them deterministically.

### 2.3 `booths.json`

Booth metadata for the 100 constituencies (~30,000 booths total — but we ship only the booth records actually referenced by the synthetic roll, ~500 entries). Each:

```json
{
  "booth_id": "151_217",
  "ac_code": "151",
  "name": "Government Higher Primary School, BTM Layout",
  "address": "8th Main, BTM Layout 2nd Stage, Bengaluru 560076",
  "lat": 12.9168,
  "lng": 77.6100,
  "accessibility": {
    "wheelchair": true,
    "ramp": true,
    "ground_floor": true,
    "language_assistance": ["Kannada", "Tamil", "Hindi", "English"],
    "sign_language": false,
    "braille_ballot": false
  },
  "voting_hours": "07:00-18:00",
  "source": "ECI Booth List Karnataka 2023, AC 151"
}
```

## 3. Sources and provenance

Every datum in the JSON files traces back to one of these public sources.

| Source | Use | URL pattern |
|---|---|---|
| ECI Statistical Reports | Past election results, turnout, margins | `eci.gov.in/statistical-report/statistical-reports/` |
| ECI Atlas of Indian Elections | Constituency-level historical context | `eci.gov.in/files/file/...atlas...pdf` |
| State CEO websites | Booth-level lists during election notifications | `ceo<state>.nic.in` |
| Census of India 2011 | Demographics (literacy, urban %) | `censusindia.gov.in` |
| Delimitation Commission notifications | Constituency boundaries | Gazette of India archives |
| Gazette of India | Form 6/8 official templates | `egazette.nic.in` |

A `data/SOURCES.md` file in the backend lists every source with date accessed.

## 4. What's synthetic, what's real

Honesty matters. So:

| Field | Real or synthetic |
|---|---|
| Constituency names, codes, boundaries | Real |
| State, district, Lok Sabha mappings | Real |
| Total electors, gender split | Real (from ECI rolls as of latest published) |
| Past election results, margins, turnout | Real |
| Demographics (literacy, urban %) | Real (Census 2011) |
| Booth names and addresses | Real (from CEO websites) |
| Booth accessibility flags | **Synthetic** — ECI does not publish booth-level accessibility data publicly. We seed plausible defaults based on booth type. Disclosed in-app. |
| Voter records (names, EPIC numbers) | **Synthetic.** Every record is fabricated. No real voter is in the dataset. |
| Voter addresses | **Synthetic** — house numbers invented; localities and PIN codes are real |

The `is_synthetic: true` flag exists on every voter record. The accessibility section of every booth is tagged `synthetic: true`. The frontend surfaces these flags as small "demo data" chips.

## 5. The disclosure surface

Three places where the user sees the data disclosure:

**On first load.** A one-line banner in the chat: *"Sankalp uses ECI's published election data and a representative voter dataset for demo. We don't access the live electoral roll."* Dismissible, persists in `localStorage`.

**In every search result.** Voter and booth cards have a small "demo data" chip with a tooltip linking to `docs/DATA.md`.

**In the README and About page.** Full disclosure section under "Assumptions and disclosures".

This is non-negotiable. A demo that pretends to be real is a demo that loses trust the moment a judge tests their own EPIC number and gets nothing.

## 6. Building the dataset

The dataset is built once, committed to the repo, and loaded in-memory at backend boot. We do not regenerate at runtime. The build script lives at `scripts/build_dataset.py` and is documented but not run during deploy.

Steps the script performs:

1. **Pull constituency master.** From a curated CSV in `scripts/inputs/ac_master.csv`, hand-extracted from ECI Statistical Reports (this is one-time, manual).
2. **Pull historical results.** Parse five elections of results from ECI PDF tables. We use `pdfplumber` to extract tables, then reconcile by hand into `scripts/inputs/election_results.csv`.
3. **Pull booth data.** From state CEO websites (where available). For the demo's 100 constituencies, this is roughly 30,000 booths, of which we sample 500.
4. **Generate synthetic voter roll.** Faker library, seeded for reproducibility. Names from name corpora per state. EPIC format follows ECI's published convention (3 letters + 7 digits, validated by the standard checksum we faux-implement).
5. **Validate.** Schema validation via Pydantic. Cross-reference checks: every voter's `ac_code` must exist in constituencies; every booth `ac_code` must exist; every voter's `booth_id` must exist.
6. **Compress.** JSON written with `compact=True`. Total size target: under 2 MB.

The build script is idempotent. Re-running produces byte-identical output (fixed seed for Faker).

## 7. Data access pattern at runtime

Boot sequence on the backend:

```python
# backend/main.py (excerpt)
@app.on_event("startup")
async def load_dataset():
    app.state.constituencies = load_json("data/constituencies.json")
    app.state.electoral_roll = load_json("data/electoral_roll.json")
    app.state.booths = load_json("data/booths.json")
    app.state.indexes = build_indexes(...)
```

Indexes built at boot:
- `epic_to_voter` — dict on `epic_number`
- `name_to_voters` — dict on `lower(name)` → list (for name search)
- `pin_to_ac` — dict on `pincode` → ac_code (handles 1:N via primary AC)
- `ac_to_booths` — dict on `ac_code` → list[booth_id]

Cold start cost (load + index): under 50 ms on Cloud Run min instance.

Memory footprint: under 30 MB resident. Cloud Run defaults give us 512 MB, plenty of headroom.

## 8. When real data becomes available

The integration seam is in `backend/tools/electoral_data.py`. Today it reads from in-memory dicts. To switch to a real backend (e.g. an ECI partner API or a partner state's CEO API):

1. Implement a new `ElectoralDataSource` class with the same interface (`search_by_epic`, `search_by_name_dob`, `lookup_booth`, `get_constituency`, `get_history`).
2. Update the dependency injection at app startup to instantiate the real source instead of the mock.
3. Add the API key to Secret Manager. Update `DEPLOYMENT.md`.

No agent, no tool, no UI component needs to change. This is the reason for the abstraction — Sankalp is built so the demo data can be swapped for real data without touching anything north of the data layer.

## 9. Privacy

Even though all voter data is synthetic, the same handling rules apply as if it were real:

- No voter records are sent to Gemini in full. The agent only sees the fields necessary for the current task.
- Names and addresses in Firestore session state are TTL'd to 24 hours.
- Logs are filtered through a structured-logging redactor that strips fields named `name`, `address`, `epic_number`, `dob`, `mobile`, `email` from any log line.
- The `cost_log` writes only token counts and agent names — never user content.

## 10. What we'd extend with more time

- Coverage to all 4,123 ACs and 543 PCs (currently 100 ACs).
- Time-series data — booth-level turnout per hour on polling day for past elections (interesting for the StoryAgent narrative).
- Demographic depth — age cohort splits, occupation splits where available.
- Real-time sync with state CEO portals for booth changes during election notifications.
- Partner integration with a state CEO for live electoral roll lookups (requires DPDP-compliant data handling).

These are out of scope for hackathon, in scope for v1.
