# Sankalp

> **Your democracy, decoded. In your language.**
>
> A multimodal, multilingual voter-journey agent that collapses voters.eci.gov.in's seven fragmented services into one conversation.

[![Live Demo](https://img.shields.io/badge/Live-Cloud_Run-4285F4?style=flat-square&logo=googlecloud)](https://sankalp-frontend-93037232246.asia-south1.run.app)
[![Built with ADK](https://img.shields.io/badge/Built_with-Google_ADK-FF6F00?style=flat-square)](https://google.github.io/adk-docs/)
[![Gemini 2.5](https://img.shields.io/badge/Gemini-2.5_Pro%2FFlash-1A73E8?style=flat-square)](https://ai.google.dev/gemini-api)
[![Hackathon](https://img.shields.io/badge/Hack2skill-PromptWars_3-blueviolet?style=flat-square)](https://vision.hack2skill.com/event/promptwars3)

---

## The problem in one paragraph

India has 970+ million registered voters, but the official voter portal exposes seven disconnected services — Form 6, Form 7, Form 8, Form 8A, electoral-roll search, application tracking, NGSP grievance — each with its own UI, language coverage, and failure mode. First-time voters bounce. Senior and rural voters give up. Disabled voters never find Form 12. The information exists; the journey doesn't.

## What Sankalp does

Sankalp is a single conversational agent that walks any Indian voter — first-timer, migrant, senior, PwD — from "I'm confused" to "I'm registered, verified, and know my polling booth" in under five minutes, in their language, via voice, camera, or text.

The killer feature is **Why YOUR vote matters** — a generative civic narrative. Drop your PIN code or EPIC number, and Sankalp pulls your constituency's historical margins, demographic shifts, and booth history; Gemini 2.5 Pro narrates a personalized 30-second story; Imagen renders the cover. Most past-five elections in India have been decided by margins under 5,000 votes. Sankalp shows users theirs.

## The chosen vertical

**Election Process Education** (Hack2skill PromptWars 3 — Track 1).

Sankalp is built around a single persona — *Riya, 19, first-time voter in Bengaluru South, Kannada-Hindi-English speaker* — and a single promise: she should never have to read a government form to vote.

## How it works

Five Google ADK agents on Cloud Run, coordinated via the AgentTool pattern.

```
                       ┌──────────────────────────┐
   user (web/voice)──▶ │   OrchestratorAgent      │  Gemini 2.5 Flash
                       │  (lang detect + routing) │  routes intent
                       └────────────┬─────────────┘
                                    │
        ┌────────────────┬──────────┼───────────┬─────────────────┐
        ▼                ▼          ▼           ▼                 ▼
 RegistrationAgent  VerificationAgent  BoothAgent      StoryAgent
   Form 6 + 8 fill    EPIC search +     Maps + access   Civic narrative
                      duplicate check                    (Gemini 2.5 Pro
                                                          + Imagen 3)
```

Each agent owns a slice of the ECI workflow. The orchestrator never does work itself — it routes. Specialists never talk to each other directly — they bubble back through the orchestrator. This keeps state in one place (Firestore) and cost predictable (Flash routes, Pro narrates).

A full system walkthrough lives in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). Agent contracts are in [`docs/AGENTS.md`](docs/AGENTS.md).

## Approach and logic

Three design choices drive everything else.

**One.** The voter never sees a "form". Forms exist in the backend; the user sees a conversation. The RegistrationAgent collects the same fields Form 6 asks for, but conversationally, in the user's language, with examples. At the end, Sankalp generates a pre-filled Form 6 PDF the user takes to voters.eci.gov.in. We don't replace the official process — we make it walkable.

**Two.** Multimodal is not a gimmick; it's the accessibility layer. Senior voters use voice. Migrant workers without English literacy use voice. PwD voters use voice. Camera input lets a 60-year-old photograph their old EPIC card and have Form 8 (corrections) auto-filled — no typing required. This is built on Gemini Live API and Cloud Vision OCR, not a custom stack.

**Three.** The civic narrative exists because awareness without emotion doesn't move people. Knowing "your last election was decided by 423 votes" changes voter behavior. The StoryAgent is what makes Sankalp memorable to a judge and useful to a citizen.

## Assumptions and disclosures

- **Data source.** voters.eci.gov.in does not expose a public API. Sankalp ships with a curated mock data layer covering ~100 representative Lok Sabha and Vidhan Sabha constituencies, sourced from ECI's published Statistical Reports (PDFs available at eci.gov.in/statistical-report/). The integration pattern is production-ready; the demo data is representative. This is disclosed in-app and in [`docs/DATA.md`](docs/DATA.md).
- **PII handling.** No EPIC numbers, names, or addresses are persisted. Session state in Firestore uses an opaque session ID and TTLs to 24 hours. No real PII is sent to Gemini — placeholder names are used for narrative generation.
- **Form submission.** Sankalp does not submit forms to ECI on the user's behalf. It generates a pre-filled PDF the user submits themselves. This is a deliberate trust boundary.
- **Languages at launch.** English, Hindi, Bengali, Tamil, Kannada, Telugu, Marathi. More can be added by extending the language-detect tool — Gemini handles all 22 scheduled languages natively.

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | Next.js 14 App Router, TypeScript, Tailwind, shadcn/ui | Mobile-first, fast, accessible primitives |
| 3D map | React Three Fiber | Reused pattern from prior project (PULSE) |
| Backend | Python 3.11, FastAPI, SSE streaming | Same pattern as Bruhworking, ships fast |
| Agents | Google ADK 0.4+, AgentTool pattern | Native tool routing, low-friction Cloud Run deploy |
| LLMs | Gemini 2.5 Flash (routing), Gemini 2.5 Pro (story) | Flash for cost discipline, Pro only when narrative quality matters |
| Voice | Web Speech API (push-to-talk) | Browser-native STT, free, sub-second latency; PRD §6 documented fallback for Gemini Live (which is the v2 distribution play) |
| OCR | Cloud Vision API | Robust on noisy phone-camera EPIC scans |
| Storage | Firestore (sessions), Cloud Storage (story assets) | Serverless, free tier covers demo |
| Maps | Google Maps Platform (Places, Directions) | Booth location + accessibility metadata |
| Deploy | Cloud Run, asia-south1 | Single region, low cold-start, free tier |

## Repo layout

```
.
├── README.md                ← you are here
├── CLAUDE.md                ← instructions for Claude Code agent
├── docs/
│   ├── ARCHITECTURE.md      ← system design + data flow
│   ├── AGENTS.md            ← five agent contracts
│   ├── PRD.md               ← product requirements + user journeys
│   ├── DATA.md              ← mock data strategy + ECI sources
│   ├── DEPLOYMENT.md        ← Cloud Run setup + env vars
│   └── ROADMAP.md           ← seven-day build plan
├── backend/                 ← FastAPI + ADK agents
│   ├── agents/
│   ├── tools/
│   ├── data/                ← mock constituency data
│   ├── main.py
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                ← Next.js 14
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── public/
│   └── package.json
└── scripts/
    ├── deploy.sh
    ├── seed_data.py
    └── smoke_test.sh
```

## Running locally

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export GOOGLE_API_KEY=...
export GOOGLE_MAPS_API_KEY=...
uvicorn main:app --reload --port 8080

# Frontend (separate terminal)
cd frontend
pnpm install
pnpm dev
```

Full setup, env vars, and Cloud Run deploy in [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

## Demo

- **Frontend (chat UI):** https://sankalp-frontend-93037232246.asia-south1.run.app
- **Permalink example:** https://sankalp-frontend-93037232246.asia-south1.run.app/story/KA-151
- **Backend (FastAPI):** https://sankalp-backend-93037232246.asia-south1.run.app · `/api/healthz` returns `{"status":"ok","version":"1.0.0",…}`

Demo script (90 seconds):
1. Riya opens the app, picks Kannada (or any of the 7 launch languages).
2. Voice or text: *"naanu first time voter, register maaDbEku"* → OrchestratorAgent routes to RegistrationAgent which collects Form 6 fields conversationally in Kannada.
3. RegistrationAgent generates a pre-filled Form 6 PDF; the chat surfaces a download card with a QR to voters.eci.gov.in.
4. Riya taps the camera icon, photographs her old EPIC card → Cloud Vision OCR (multi-strategy) parses `ABC1234567` → auto-routes to VerificationAgent which renders her voter record.
5. "Where do I vote?" → BoothAgent surfaces a booth card with accessibility chips and Google Maps deeplink.
6. "Why does my vote matter?" → StoryAgent (Gemini 2.5 Pro) writes a 200-word personalised narrative about Bommanahalli's 4,218-vote margin in 2023 — rendered with an Imagen 3 cover and a stylised React Three Fiber constituency scene. Share button copies a permalink at `/story/KA-151`.

## Phase log

| Phase | Ship | Commit |
|-------|------|--------|
| 0 | Repo scaffold, GCP wiring, Hello-World deploy | `5542b44` |
| 1 | Mock electoral data layer (100 ACs, 4,500 voters, 510 booths, 5 personas) | `db8b105` |
| 2 | Five Google ADK agents + 12 tools, prompts byte-verbatim from `docs/AGENTS.md` | `cb40816` |
| 3 | FastAPI backend with SSE streaming, structured logging, cost-log to Firestore | `3cadfb9` |
| 4 | Next.js 14 chat UI, 7-language i18n, Web Speech voice, marker→component dispatch | `38c89dd` |
| 5 | Multi-strategy OCR (DOCUMENT→TEXT fallback, regex+heuristics, dataset cross-check) + EpicCamera | `24b8005` |
| 6 | StoryAgent prompt evolution + 5 Imagen covers + R3F constituency scene + permalink + cost endpoint | `c902e57` |
| 7 | Polish, version bump v1.0.0, DoD walk, smoke green, tag pushed | this commit |

Phase-cumulative LLM spend across the seven-day build: **≈ $0.50** (well under the $5 ceiling). Live test runs and 10-AC narrative sweeps logged in Firestore `cost_log`; aggregations available at `/api/admin/costs?key=…`.

## Evaluation rubric self-check

| Rubric | Where it shows up |
|---|---|
| Code quality | Typed Pydantic contracts between agents, monorepo, single branch |
| Security | No persistent PII, hashed session IDs, secrets in Secret Manager, no key in repo |
| Efficiency | Flash routes, Pro narrates only on explicit request, Firestore TTLs, single region |
| Testing | 84 hermetic backend tests + 23 frontend vitest + 4 live (`pytest -m live`) covering Vertex AI / Cloud Vision / SSE end-to-end |
| Accessibility | Voice-first, 7 languages at launch, WCAG AA contrast, screen-reader labels |
| Google services | Gemini, ADK, Cloud Run, Maps, Firestore, Vision OCR, Cloud Storage, Imagen — eight |

## License

MIT. See [LICENSE](LICENSE).

## Author

Built solo by [Oikantik Basu](https://github.com/Golden007-prog) for Hack2skill PromptWars 3.
