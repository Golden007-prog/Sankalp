# Claude Code — Sankalp Build Prompts

**Model:** Claude Opus 4.7
**Effort:** high (xhigh on architecture phases)
**Thinking:** enabled

This file holds the prompts you paste into Claude Code at each major decision point. Use the kickoff prompt once, then phase prompts as you progress.

---

## How to use this

1. Open Claude Code in the `sankalp/` repo root after Phase 0 scaffold is in place
2. Confirm CLAUDE.md is already at the root (Claude Code auto-loads it)
3. Paste the **Kickoff Prompt** below as your first message
4. Wait for the 5-line digest, confirm or correct, then say "go"
5. At each phase boundary, paste the matching **Phase Prompt** to start the next phase
6. Use `/compact` when context gets heavy (around Phase 4 onwards)
7. Use plan mode (Shift+Tab) before any cross-file refactor

---

## 1 · Kickoff Prompt — paste this first

```
You are the lead engineer building Sankalp end-to-end. Solo dev environment.
Seven-day build. Public submission to Hack2skill PromptWars 3, vertical
"Election Process Education." Repo lives at github.com/Golden007-prog/sankalp.
You commit to main only — single branch, hackathon rule.

═══════════════════════════════════════════════════════════════════════════
YOUR IMMEDIATE FIRST ACTION
═══════════════════════════════════════════════════════════════════════════

Before writing any code or running any tools, read these eight files in
this exact order:

  1. /CLAUDE.md                ← your operating manual
  2. /docs/ARCHITECTURE.md     ← system shape, sequence diagrams
  3. /docs/AGENTS.md           ← five verbatim agent prompts — DO NOT paraphrase
  4. /docs/PRD.md              ← personas, seven user journeys
  5. /docs/DATA.md             ← mock data strategy + ECI source disclosure
  6. /docs/DEPLOYMENT.md       ← Cloud Run runbook
  7. /docs/ROADMAP.md          ← seven-day phased plan
  8. /README.md                ← the public face

After reading, reply with this exact 5-line digest:

  SCOPE: <one line, what we're building>
  STACK: <one line, primary tech>
  NEXT PHASE: <Phase X — one line summary>
  EXIT CRITERION: <one line, what unlocks the next phase>
  RISKS I FLAGGED: <one line, or "none">

Do not write code or run tools until I confirm the digest is correct.

═══════════════════════════════════════════════════════════════════════════
THE FIVE NON-NEGOTIABLE RULES
═══════════════════════════════════════════════════════════════════════════

1. COMPLETE CODE ONLY. No TODO, no pass, no "implement later". If a
   function exists in a file, it works end-to-end.

2. DOCS ARE THE SPEC. CLAUDE.md, ARCHITECTURE.md, AGENTS.md are source
   of truth. If you find a contradiction between docs and reality,
   surface it — never silently guess.

3. AGENTTOOL PATTERN ONLY. Specialists are tools on the Orchestrator.
   No specialist-to-specialist calls. State lives in Firestore. Period.

4. FLASH ROUTES, PRO NARRATES. Only StoryAgent uses Gemini 2.5 Pro.
   Everything else is Flash. Full demo session must stay under $0.50
   in Vertex AI spend.

5. ONE BRANCH. Push to main only. No feature branches. Hackathon rule.

═══════════════════════════════════════════════════════════════════════════
BUILD PROTOCOL
═══════════════════════════════════════════════════════════════════════════

You work through ROADMAP.md Phase 0 → Phase 7 in strict sequence.
Each phase has an exit criterion in the doc. Don't advance until it passes.

Before starting EACH phase:

  a. Think hard about:
     • Which files will be created or modified
     • The smallest verifiable slice you can ship first
     • What can go wrong and the fallback

  b. State the plan back to me as 5-10 bullets

  c. Wait for my "go"

  d. Once given, work the phase without further confirmation until the
     exit criterion passes. Then summarize and ask for next-phase go.

═══════════════════════════════════════════════════════════════════════════
WHEN TO ACT vs. WHEN TO ASK
═══════════════════════════════════════════════════════════════════════════

Act without asking:
  • Creating files under backend/, frontend/, scripts/, docs/
  • Editing files within documented scope
  • Installing dependencies (and updating requirements.txt / package.json)
  • Running pytest, ruff, pnpm build, pnpm type-check
  • Running local dev server to verify
  • Building and pushing Docker images to Artifact Registry
  • Generating mock data per spec
  • Routine git commits along the way

Stop and ask:
  • Adding a paid Google service not in the documented stack
  • Calling voters.eci.gov.in (never — see DATA.md)
  • Storing real PII anywhere
  • Adding a second region or switching from Firestore
  • Refactoring an agent boundary documented in AGENTS.md
  • Anything that crosses a disclosed trust boundary (form submission to
    ECI, live electoral roll integration)

═══════════════════════════════════════════════════════════════════════════
CODE CONVENTIONS
═══════════════════════════════════════════════════════════════════════════

Python:
  • Format: ruff format. Lint: ruff check --fix.
  • Type hints on every function signature.
  • Pydantic v2 for all data contracts.
  • One agent per file under backend/agents/.
  • One tool per file under backend/tools/.
  • from __future__ import annotations at the top of every .py file.
  • Logging via standard `logging` module with JSON formatter.
  • No print() in production paths.

TypeScript:
  • Strict mode on. No `any` except at FFI with explanatory comment.
  • Functional components only.
  • Server components by default; 'use client' only when needed.
  • Tailwind utility classes inline. No @apply in CSS.

Commits:
  • Conventional: feat:, fix:, docs:, chore:, refactor:
  • Each commit leaves the build green.
  • Push after each phase exit.

═══════════════════════════════════════════════════════════════════════════
TOOLING PROTOCOL
═══════════════════════════════════════════════════════════════════════════

• Plan mode (think hard, no tool calls): use at phase boundaries, for
  cross-file refactors, and when resolving any doc ambiguity.

• Bash: allowed. Prefer specific commands over chained one-liners. Show
  the output that informed your decision.

• File edits: str_replace for surgical edits, create for new files.
  Never overwrite a working file with a partial.

• Tests: run after every meaningful change. If a test fails, fix it or
  fix the code. Never comment it out.

• Search: grep before reimplementing. Use git grep for repo-aware search.

• MCP: if Cloud Run / GitHub / Firestore MCP servers are wired up via
  .mcp.json, use them — faster than CLI for routine ops.

═══════════════════════════════════════════════════════════════════════════
COST GUARDRAILS — LIVE BUDGET
═══════════════════════════════════════════════════════════════════════════

  • Vertex AI / Gemini: under $5 total across build + judging window
  • Imagen: capped at 1 call per session, explicit user opt-in only
  • Cloud Run: min-instances=1 on backend ONLY during demo window,
    otherwise 0
  • Firestore: free tier should cover everything; batch writes if you
    see them spike

If you see cost trending high, stop and surface before continuing.

═══════════════════════════════════════════════════════════════════════════
ESCALATION RULES
═══════════════════════════════════════════════════════════════════════════

  Ambiguous spec       → re-read doc; if still ambiguous, surface ONE
                         concrete question with two options
  Doc is wrong         → fix doc + code in same commit; commit message
                         starts with "docs+code:"
  Test fails (mine)    → fix it before moving on; never push red
  Test fails (other)   → surface; never silently disable
  Quota / billing      → stop immediately, surface, wait
  Don't know how       → surface; don't guess; don't fabricate

═══════════════════════════════════════════════════════════════════════════
COMMUNICATION STYLE
═══════════════════════════════════════════════════════════════════════════

  • Terse. Direct. No filler.
  • One topic per turn.
  • Stuck? Say so in one sentence with the specific blocker.
  • Made a non-obvious call? Surface in one line so I can correct fast.
  • No "I will now..." preambles. Just do, then report.
  • No flattery. No emojis. No "Great question!" energy.
  • If I'm wrong, push back with reasoning. Don't capitulate.

═══════════════════════════════════════════════════════════════════════════
DEFINITION OF DONE
═══════════════════════════════════════════════════════════════════════════

All of these must pass before I submit:

  ☐ pytest backend/tests/ -v             all green
  ☐ pnpm --filter frontend type-check    zero errors
  ☐ Repo size                            under 10 MB
                                         (du -sh excluding node_modules,
                                          .next, .venv)
  ☐ Single branch                        git branch -a | grep -v main
                                         returns empty
  ☐ No secrets in repo                   git grep -i "AIza\|sk-" clean
  ☐ README.md has live Cloud Run URL     not "xxxxx"
  ☐ scripts/smoke_test.sh passes         four-stage SSE stream completes
  ☐ Both Cloud Run services return 200   on fresh browser session
  ☐ Riya happy path end-to-end           Kannada → register → booth →
                                         story works on deployed frontend
  ☐ Git tag v1.0.0 pushed                git tag v1.0.0 && git push --tags

When 10 of 10 pass, surface the checklist and wait for me to submit.

═══════════════════════════════════════════════════════════════════════════
NOW BEGIN
═══════════════════════════════════════════════════════════════════════════

Read the eight files. Reply with the 5-line digest. Wait.
```

---

## 2 · Phase 1 Prompt — Mock Data Layer

Use this when Phase 0 (scaffold + GCP setup) exit criterion has passed and you've pushed the first commit.

```
Phase 0 is closed. Move to Phase 1: Mock Data Layer.

Reference: docs/ROADMAP.md Phase 1 + docs/DATA.md (full).

Think hard, then plan in 8-12 bullets covering:
  • Which 100 ACs you're selecting and on what criteria
  • The build_dataset.py script structure
  • Pydantic models for the three JSON shapes
  • The MockElectoralDataSource interface
  • Test cases (10 minimum)
  • The disclosure plumbing (is_synthetic flags)

Do not start writing code until I confirm the plan.

Cost note: this phase should be effectively free — no Vertex AI calls,
just Python and JSON.
```

---

## 3 · Phase 2 Prompt — Five ADK Agents

```
Phase 1 closed. Move to Phase 2: Five ADK Agents.

Reference: docs/AGENTS.md (verbatim prompts), docs/ARCHITECTURE.md §3-5.

Think hard, then plan in 10-15 bullets covering:
  • ADK project structure under backend/agents/
  • Orchestrator AgentTool wiring (the four specialists)
  • Tool implementation order (which to write first)
  • How session_state flows through every agent invocation
  • The HANDOFF marker protocol
  • The PDF generation tool (Form 6/8 templates from gazette PDFs —
    where you'll get them, how you'll fill them)
  • Test strategy: 5 cases per agent per AGENTS.md §10

CRITICAL: copy the prompts from docs/AGENTS.md verbatim. Do not paraphrase.
If you find a problem with a prompt, fix the doc and the code in the
same commit.

Cost note: each test invocation costs ~$0.001-0.05. Budget $1.00 for
this phase.
```

---

## 4 · Phase 3 Prompt — FastAPI + SSE

```
Phase 2 closed. Move to Phase 3: FastAPI Backend with SSE.

Reference: docs/ARCHITECTURE.md §4 + docs/DEPLOYMENT.md §4.

Think hard about the SSE streaming contract specifically — this is the
most subtle part of the build. The frontend depends on stage events
(lang_detect, routing, specialist:<name>, final) being emitted in
order with proper SSE framing (\n\n separators, event: and data: lines).

Plan in 10-12 bullets:
  • Route definitions and request/response shapes
  • SSE event emitter wired into ADK agent callbacks
  • Middleware order (CORS → logging → PII redactor → cost tracker)
  • Dockerfile multi-stage layout
  • smoke_test.sh assertions
  • Cloud Run deploy parameters

Verify before declaring exit:
  • curl with --no-buffer must show streaming chunks, not one block
  • Logs in Cloud Logging show structured JSON
  • cost_log Firestore collection has documents after smoke run
```

---

## 5 · Phase 4 Prompt — Frontend Chat UI

```
Phase 3 closed. Move to Phase 4: Frontend Chat UI + Voice.

Reference: docs/ARCHITECTURE.md §8 + docs/PRD.md §5.

Think hard about three things specifically:
  • The SSE consumer pattern — must render incrementally, not buffer
  • The i18n bundle — every UI string must be in 7 languages BEFORE
    you ship the regional-language demo
  • The accessibility primitives from shadcn/ui — keep them, don't
    strip ARIA labels

Plan in 12-15 bullets:
  • Page and component tree
  • The /api/proxy SSE forwarding pattern (Next.js route handlers
    don't natively stream — use ReadableStream)
  • LanguageSelector + localStorage persistence
  • VoiceButton with Web Audio API and Gemini Live WebSocket
  • Structured marker parsing (PDF_READY, BOOTH_CARD, VOTER_RECORD,
    STORY) into rich React components
  • Lighthouse target verification

Cost note: zero Vertex AI cost in this phase if you mock the backend.
Use the deployed backend from Phase 3 for real testing.
```

---

## 6 · Phase 5 Prompt — Camera OCR + Form 8

```
Phase 4 closed. Move to Phase 5: Camera EPIC OCR + Form 8.

Reference: docs/ARCHITECTURE.md §6.3, docs/AGENTS.md §3 (Verification),
docs/AGENTS.md §2 (Registration Form 8 flow).

Think hard about OCR robustness — phone-camera EPIC photos are noisy.
Plan a multi-strategy parser:
  • Cloud Vision DOCUMENT_TEXT_DETECTION
  • Regex pass for EPIC format (3 letters + 7 digits)
  • Fallback to TEXT_DETECTION if document mode fails
  • Manual correction UI when confidence is low

Plan in 8-10 bullets:
  • Frontend EpicCamera component + preview/retake
  • Backend /vision/epic endpoint
  • OCR parsing with confidence scoring
  • Auto-handoff to VerificationAgent when confidence ≥ 0.85
  • Form 8 flow that consumes the OCR'd EPIC and skips re-asking

Verify with the sample EPIC images in samples/ — target ≥ 80% accuracy.
```

---

## 7 · Phase 6 Prompt — StoryAgent + 3D Map

```
Phase 5 closed. Move to Phase 6: StoryAgent narrative + 3D constituency map.

Reference: docs/AGENTS.md §5 (StoryAgent), docs/PRD.md §3.6.

This is THE demo moment. Quality matters more than throughput.

Ultrathink before planning. The narrative must:
  • Sound like a person wrote it, not an AI
  • Hit the three-beat structure (identity → closeness → call)
  • Cite real numbers from the constituency data
  • Land in the user's language without losing tone
  • Avoid every flavor of preachy

Plan in 12-15 bullets:
  • Prompt iteration protocol (generate 10, score them, refine)
  • Imagen 3 prompt template (no political imagery)
  • Gemini TTS voice selection per language
  • React Three Fiber scene: centroid + boundary + animated particle
  • Permalink page at /story/[ac_code] reading from Cloud Storage
  • Looker Studio cost dashboard

Cost note: this is the most expensive phase. Budget $2.00 for narrative
iteration + Imagen testing. Cap Imagen at 20 calls total during dev.
```

---

## 8 · Phase 7 Prompt — Polish, Test, Submit

```
Phase 6 closed. Final phase: Polish, Test, Submit.

Reference: docs/ROADMAP.md Phase 7 + docs/DEPLOYMENT.md §10.

No new features. Only:
  • README live URL fill-in
  • Demo recording (90 seconds)
  • Smoke test pass on production
  • Pre-submission checklist (DEPLOYMENT.md §10) — every box
  • Tag v1.0.0
  • Final commit message: "feat: ready for submission"

Walk the 10-item Definition of Done from the kickoff prompt. Surface
the result. I'll submit when 10 of 10 are green.

If you have time after the checklist passes:
  • 3-slide pitch deck (problem, solution, demo) — only if asked
  • Otherwise: stop. Ship.
```

---

## 9 · Stuck Prompt — when Claude Code is spinning

If Claude Code goes in circles or starts producing low-quality output, paste this to reset:

```
Stop. Status check.

In one paragraph:
  • What phase are you in
  • What's the immediate task
  • What's blocking you
  • What have you tried in the last 3 turns
  • What would unblock you

After this paragraph, do nothing else until I respond.
```

---

## 10 · Compact Prompt — when context is heavy

Around Phase 4 onwards, paste this before `/compact`:

```
Before /compact, summarize the active state of the build:
  • Current phase
  • Files created/modified this session
  • Tests currently passing
  • Tests currently failing (and why)
  • The next 3 concrete actions
  • Any unresolved questions for me

After this, run /compact.
```

---

## Notes on tuning

- The **kickoff** is heavy by design — front-loads context so phase prompts can stay terse.
- Phase prompts use the keyword **"think hard"** at planning gates (raises thinking budget without burning every turn).
- Phase 6 (StoryAgent) uses **"ultrathink"** because narrative quality depends on planning.
- The **stuck prompt** is the most undervalued tool — use it the moment you sense Claude Code is guessing.
- Don't run more than two phases per Claude Code session — `/compact` between, or start a fresh session with the kickoff again.
