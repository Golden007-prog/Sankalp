# Roadmap

The seven-day build plan. Solo, sequential, no parallel tracks. Each phase has an exit criterion. Don't move forward until it passes.

---

## Day 0 — Repo and GCP setup *(2 hours)*

**Goal:** the scaffold is in place. You can `git push` and `gcloud run deploy` (an empty service).

**Tasks**

1. Create public GitHub repo `sankalp` under `Golden007-prog`
2. Drop in this `docs/` folder, `README.md`, `CLAUDE.md`, `.gitignore`, `LICENSE` (MIT)
3. Create `backend/` and `frontend/` directories with `Hello World` placeholders
4. Run all of [`docs/DEPLOYMENT.md`](DEPLOYMENT.md) §2 — GCP project, APIs, Firestore, Storage, service account, secrets
5. Push first commit to `main`
6. Test the deploy pipeline with the placeholder backend (just to verify gcloud + Artifact Registry + Cloud Run all work end-to-end)

**Exit criterion**

- `https://sankalp-backend-xxxxx-as.a.run.app/api/healthz` returns `{"status":"ok"}` on a "Hello World" FastAPI app (bare `/healthz` is reserved by Google Frontend on `*.run.app`)
- Frontend placeholder loads at `https://sankalp-frontend-xxxxx-as.a.run.app/`
- Both repo and Cloud Run services are public

**Don't move on if:** any GCP API isn't enabled or service account is missing a role. Fixing this on day 6 is a nightmare.

---

## Day 1 — Mock data layer *(6 hours)*

**Goal:** the data layer is real. Agents have something to query.

**Tasks**

1. Hand-curate `scripts/inputs/ac_master.csv` with 100 representative ACs
2. Pull historical results from ECI Statistical Reports (5 elections × 100 ACs)
3. Pull booth metadata from state CEO sites for the demo ACs
4. Write `scripts/build_dataset.py` per [`DATA.md`](DATA.md) §6
5. Generate `constituencies.json`, `electoral_roll.json`, `booths.json` under `backend/data/`
6. Pydantic models in `backend/types/` for every record shape
7. `backend/tools/electoral_data.py` with the `ElectoralDataSource` interface and a `MockElectoralDataSource` implementation
8. Unit tests in `backend/tests/test_electoral_data.py` — 10 cases covering each lookup

**Exit criterion**

- `pytest backend/tests/test_electoral_data.py -v` — all green
- `python -c "from tools.electoral_data import MockElectoralDataSource; s = MockElectoralDataSource(); print(s.search_by_epic('ABC1234567'))"` returns a real record
- All three JSON files compress to under 2 MB total

**Don't move on if:** any voter record lacks the `is_synthetic: true` flag, or any election record lacks a `source` field.

---

## Day 2 — Five ADK agents *(8 hours)*

**Goal:** the agents work. No UI yet. You can hit them via Python.

**Tasks**

1. Set up ADK project structure under `backend/agents/`
2. Write `orchestrator.py` with the verbatim prompt from [`AGENTS.md`](AGENTS.md) §1
3. Wire the four AgentTools (registration, verification, booth, story)
4. Write each specialist agent — `registration.py`, `verification.py`, `booth.py`, `story.py` — with verbatim prompts
5. Implement the tools each agent needs:
   - `tools/language.py` (detect_language)
   - `tools/session.py` (Firestore CRUD)
   - `tools/form_pdf.py` (Form 6 + 8 PDF gen — use `pypdf` + the gazetted Form 6 PDF as template)
   - `tools/epic_search.py` (wraps `electoral_data.py`)
   - `tools/maps.py` (Maps Platform calls)
   - `tools/ocr.py` (Cloud Vision wrapper, can stub for now if behind on time)
   - `tools/constituency.py` (StoryAgent's data tools)
   - `tools/imagen.py` (Imagen 3 wrapper)
   - `tools/tts.py` (Gemini TTS wrapper)
6. Write `backend/tests/test_orchestrator.py` with 5 routing test cases
7. Write `backend/tests/test_<agent>.py` for each specialist with the 5 cases listed in [`AGENTS.md`](AGENTS.md) §10

**Exit criterion**

- All agent tests pass
- Manual smoke from Python REPL:
  ```python
  from agents.orchestrator import orchestrator
  resp = await orchestrator.run("I want to register to vote", session_id="test")
  assert "RegistrationAgent" in resp.agent_trace
  ```
- StoryAgent produces a 200-word narrative for AC code `151` (Bommanahalli) end-to-end

**Don't move on if:** any agent hallucinates a constituency that isn't in the data, or any tool call returns un-handled errors.

---

## Day 3 — FastAPI backend with SSE *(8 hours)*

**Goal:** real HTTP endpoints. The frontend can talk to it.

**Tasks**

1. `backend/main.py` — FastAPI app, CORS for Cloud Run + localhost, startup event loads dataset
2. `backend/routes/chat.py` — POST `/chat` with SSE streaming. Body: `{message, session_id, language}`. Streams `lang_detect`, `routing`, `specialist:<name>`, `final` events
3. `backend/routes/voice.py` — POST `/voice` proxying to Gemini Live API. WebSocket upgrade.
4. `backend/routes/vision.py` — POST `/vision/epic` for OCR
5. `backend/routes/health.py` — `/api/healthz` returning version + git SHA
6. Middleware: structured logging, PII redaction filter, request ID correlation
7. Cost tracking middleware that writes to Firestore `cost_log` collection
8. `Dockerfile` — multi-stage, non-root user, healthcheck
9. `scripts/smoke_test.sh` — curls `/chat` with the demo input, asserts the four-stage stream
10. Deploy to Cloud Run per [`DEPLOYMENT.md`](DEPLOYMENT.md) §4

**Exit criterion**

- Smoke test passes against the deployed backend
- `/chat` SSE stream completes in under 5s for the registration intent
- Logs in Cloud Logging show structured JSON with `session_id`, `intent`, `latency_ms`
- The cost_log Firestore collection has at least one document after a smoke run

**Don't move on if:** SSE buffering is happening (responses come in one chunk instead of streaming). This often means the proxy/CDN config is wrong.

---

## Day 4 — Frontend chat UI + voice *(10 hours)*

**Goal:** a real user can have a real conversation through the UI.

**Tasks**

1. `frontend/` — Next.js 14 App Router, TypeScript, Tailwind, shadcn/ui
2. Top-level layout with language selector, dark/light toggle, large-text toggle
3. `app/(chat)/page.tsx` — chat UI: message list, composer, voice button, camera button
4. `components/ChatStream.tsx` — consumes SSE from `/api/proxy/chat`, renders staged events with chips
5. `components/LanguageSelector.tsx` — 7 languages, persists to localStorage
6. `components/VoiceButton.tsx` — push-to-talk via Web Audio API + Gemini Live
7. `components/MessageBubble.tsx` — text + markdown rendering, structured marker parsing
8. `components/BoothCard.tsx` — Map embed + accessibility chips + ETA
9. `components/FormPdfCard.tsx` — download CTA + QR code to ECI portal
10. Internationalization bundle in `frontend/i18n/` for UI strings (7 languages)
11. Deploy to Cloud Run per [`DEPLOYMENT.md`](DEPLOYMENT.md) §5

**Exit criterion**

- The full registration flow works in Hindi, English, and one regional language end-to-end through the UI
- Voice button captures audio, streams to backend, gets back text, renders correctly
- Lighthouse score on mobile: Performance 80+, Accessibility 95+
- The deployed frontend talks to the deployed backend without CORS errors

**Don't move on if:** any UI string is hard-coded in English. If the i18n bundle has gaps, the regional-language demo will fall back to English mid-sentence and that's the worst look on stage.

---

## Day 5 — Camera EPIC OCR + Form 8 *(10 hours)*

**Goal:** the camera flow works. This is half the senior-voter demo.

**Tasks**

1. `components/EpicCamera.tsx` — `<input capture="environment">`, preview, retake, submit
2. Frontend POST to `/api/proxy/vision/epic` → forwarded to backend `/vision/epic`
3. Backend: Cloud Vision text detection, parse EPIC fields with regex + heuristics
4. `tools/ocr.py` returns a normalized `ParsedEpic` model
5. Hand off to VerificationAgent automatically — Orchestrator sees `session.last_ocr` set and routes
6. RegistrationAgent's Form 8 flow consumes the OCR'd EPIC number and skips re-asking it
7. End-to-end test: photograph a sample EPIC card → get verification result → trigger Form 8 → download corrected PDF
8. Add this flow to `scripts/smoke_test.sh`

**Exit criterion**

- Photographing a printed sample EPIC (provided in `samples/`) yields the correct EPIC number 9 times out of 10
- Form 8 PDF is generated end-to-end from the OCR result
- The flow works on mobile Safari and Chrome (both desktop and mobile UA)

**Don't move on if:** OCR accuracy is below 80% on clean printed samples. Tune the prompt or add a manual-correction step before moving on.

---

## Day 6 — StoryAgent narrative + 3D map *(8 hours)*

**Goal:** the demo moment is real.

**Tasks**

1. StoryAgent prompt tuning — generate narratives for 10 different ACs and verify quality. Iterate the prompt until you'd be proud to show the worst of those 10 to a judge.
2. `tools/imagen.py` — Imagen 3 cover generation. Prompt template excludes political imagery.
3. `tools/tts.py` — Gemini TTS in 7 languages. Test all voices.
4. Frontend `components/StoryCanvas.tsx` — React Three Fiber constituency mini-map. Centroid + boundary polygon + animated "your vote" particle
5. Story permalink — `app/story/[ac_code]/page.tsx` reads from Cloud Storage and renders the saved story
6. Share button (Web Share API) — copies permalink + opens native share sheet on mobile
7. Looker Studio dashboard in GCP for the cost_log — 4 charts (cost per agent, latency P95, tokens per session, sessions per hour). Public link in README.

**Exit criterion**

- Stories render cleanly for at least 5 different ACs across 3 languages
- Imagen covers don't trigger content filter on any of the 10 test ACs
- The 3D map renders on iPhone and Android Chrome under 2 seconds
- The cost dashboard shows real data and is shareable

**Don't move on if:** the narrative reads "preachy" or "AI-generated" rather than "personal". This is the demo moment. Iterate the prompt until it lands.

---

## Day 7 — Polish, test, submit *(6 hours)*

**Goal:** ready for the judges.

**Tasks**

1. Final pass on README — fill in live Cloud Run URL, demo screenshots, badges
2. Record a 90-second demo video. Upload to YouTube unlisted, link in README.
3. Run the full smoke test suite. Fix any flaky test.
4. Run [`DEPLOYMENT.md`](DEPLOYMENT.md) §10 pre-submission checklist
5. Final commit to `main` with message `feat: ready for submission`
6. Tag the release: `git tag v1.0.0 && git push --tags`
7. Submit on the Hack2skill portal:
   - Challenge: Election Process Education
   - GitHub URL: `https://github.com/Golden007-prog/sankalp`
   - Deployed URL: the Cloud Run frontend URL

**Exit criterion**

- Submission accepted on Hack2skill portal
- Both URLs return 200 from a fresh browser session
- A friend who's never seen the project can complete one full journey from the deployed URL using only your README

**If you have time left:**
- Sleep
- Or: a 3-slide pitch deck (problem, solution, demo) — doesn't hurt for the judging round

---

## What goes wrong, and what you do about it

### "I'm behind on Day 3"

Cut: voice input. Cut: camera input. Ship the text-only chat. The four agents and the story narrative are the core. Everything else is gravy.

### "I'm behind on Day 5"

Cut: camera OCR. Show the manual-entry path. Be honest in the README that camera OCR is "designed but not shipped due to time".

### "I'm behind on Day 6"

The story narrative is non-negotiable — it's your differentiator. Cut the 3D map, cut the Imagen cover, cut the TTS. Ship just the text narrative beautifully formatted. The story still wins.

### "Day 7 and the deploy is broken"

You have three submission attempts. The first attempt should go in by end of Day 6 as a backstop, even if rough. Day 7 is the polish attempt. Day 8 (if available) is the recovery attempt.

### "A model isn't responding well"

Don't tune the model — tune the prompt. The prompts in [`AGENTS.md`](AGENTS.md) are starting points. If you change them, update the doc in the same commit.

### "GCP quota or billing issue mid-build"

Have a backup billing account ready. Have the Vertex AI quota check page bookmarked. Don't burn 2 hours debugging quotas at midnight on Day 6.

---

## What you do not do during this build

- Add a feature not in this doc without updating this doc first
- Switch from ADK to LangChain "to try something"
- Add Stripe or Razorpay (this is not a payments product)
- Build native iOS/Android — PWA is enough
- Refactor agents to use Pub/Sub fan-out (we evaluated, decided no, see [`ARCHITECTURE.md`](ARCHITECTURE.md) §2)
- Add authentication (anonymous-only)
- Scope-creep into result tracking, candidate info, or news aggregation

Each of these is a real product idea. None of them belong in this hackathon.
