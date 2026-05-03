# CLAUDE.md

Instructions for the Claude Code / Antigravity build agent working on Sankalp.

Read this file first. Then read `docs/ARCHITECTURE.md` and `docs/AGENTS.md` before writing any code.

---

## Project identity

- **Name:** Sankalp
- **Tagline:** *Your democracy, decoded. In your language.*
- **What it is:** A multimodal voter-journey agent for Indian elections, built on Google ADK and deployed to Cloud Run.
- **What it is not:** A chatbot. A FAQ widget. A ChatGPT wrapper.
- **Hackathon:** Hack2skill PromptWars 3, vertical = Election Process Education.
- **Submission constraints:** public GitHub repo, single branch, under 10 MB, max three submission attempts.

## Build philosophy

Five rules. Non-negotiable.

1. **Write complete code.** No `# TODO`, no `pass`, no `// implement later`. If a function is in the file, it works end-to-end.
2. **Read the docs first.** `docs/ARCHITECTURE.md` and `docs/AGENTS.md` are the source of truth. Don't invent agent boundaries.
3. **Use the AgentTool pattern.** Specialists are wrapped as tools on the Orchestrator. No direct specialist-to-specialist calls. State lives in Firestore, not in agent memory.
4. **Flash routes, Pro narrates.** Only StoryAgent uses Gemini 2.5 Pro. Everything else uses Flash. Cost discipline matters — target under $5 across the full demo session.
5. **Ship one branch.** Push to `main` only. No feature branches. Hackathon rule.

## What you are allowed to do without asking

- Create new files under `backend/`, `frontend/`, `scripts/`, `docs/`
- Edit existing files
- Install Python or Node dependencies (and update `requirements.txt` / `package.json`)
- Run tests, linters, type-checkers
- Run the local backend or frontend dev server to verify
- Generate mock data for the 100 representative constituencies
- Build and push Docker images to Artifact Registry

## What you must ask before doing

- Adding a paid Google service that isn't already in the stack (current stack: Gemini, ADK, Cloud Run, Maps, Firestore, Vision, Cloud Storage, Imagen)
- Hitting voters.eci.gov.in directly (do not — see `docs/DATA.md`)
- Submitting forms to any government endpoint
- Persisting anything that looks like real PII
- Adding a second region beyond asia-south1
- Switching from Firestore to Cloud SQL or any other database

## Stack

```
Frontend:  Next.js 14 App Router · TypeScript · Tailwind · shadcn/ui · React Three Fiber
Backend:   Python 3.11 · FastAPI · sse-starlette · Google ADK 0.4+
LLMs:      Gemini 2.5 Flash (routing/specialists) · Gemini 2.5 Pro (StoryAgent only)
Voice:     Gemini Live API
OCR:       Cloud Vision API
Storage:   Firestore (sessions, TTL 24h) · Cloud Storage (generated story assets)
Maps:      Google Maps Platform (Places + Directions)
Deploy:    Cloud Run, asia-south1, single region
Auth:      None for hackathon (anonymous sessions, opaque IDs)
```

## Build order (follow exactly)

The phased plan lives in `docs/ROADMAP.md`. Summary:

1. **Phase 0** — repo scaffold, .gitignore, .env.example, GCP project setup
2. **Phase 1** — mock constituency data layer + Firestore schema + Pydantic types
3. **Phase 2** — five ADK agents with prompts and tools (no UI yet)
4. **Phase 3** — FastAPI backend with SSE streaming endpoints
5. **Phase 4** — Next.js chat UI + language selector + voice input
6. **Phase 5** — camera EPIC OCR + Form 8 auto-fill flow
7. **Phase 6** — StoryAgent narrative + 3D constituency map
8. **Phase 7** — Cloud Run deploy, smoke test, demo recording

After each phase, run the verification step listed in `ROADMAP.md`. Don't move forward until it passes.

## Code conventions

**Python.**
- Format with `ruff format`. Lint with `ruff check`.
- Type hints on every function signature. `from __future__ import annotations` at the top of every file.
- Pydantic v2 for all data contracts.
- One agent per file under `backend/agents/`. Tools under `backend/tools/`.
- No `print` in production code — use `logging`.

**TypeScript.**
- Strict mode on. No `any` except at FFI boundaries with a comment explaining.
- Components are functional. No class components.
- Server components by default; `'use client'` only when interactivity is needed.
- Tailwind utility classes inline, no `@apply` in CSS files.

**Commits.**
- Conventional commits: `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`.
- Each commit should leave the build green.
- Squash merge from local branches if you use them, but push to `main`.

## Agent prompt rules

Every ADK agent prompt in `backend/agents/` follows this structure:

```
ROLE: one sentence
CONTEXT: where this agent sits in the system
INSTRUCTIONS: numbered list, imperative voice
TOOLS: explicit list with one-line description each
OUTPUT FORMAT: structured (JSON schema reference) or natural language
GUARDRAILS: what this agent will not do
LANGUAGE: respond in the user's selected language ({language_code})
```

See `docs/AGENTS.md` for full prompts per agent. Do not paraphrase — copy them verbatim into the agent file.

## Cost guardrails

- Max tokens per agent response: 2048 (Flash), 4096 (Pro StoryAgent only).
- Imagen calls: max 1 per session, only on explicit user "show me a cover" tap.
- Gemini Live: max 5-minute session, then re-prompt to text.
- Firestore reads/writes: batched; no per-keystroke writes.
- Target: under $5 of Vertex AI spend across the full demo + judging window.

## Testing

- **Backend unit tests** under `backend/tests/`. One file per agent. Mock Gemini responses with `unittest.mock`.
- **End-to-end smoke test** in `scripts/smoke_test.sh` — curls the SSE endpoint with a known input and asserts the four-stage stream completes.
- **Frontend** — Playwright test for the registration happy path. Skip if time pressure forces it.
- Run all tests before every push to `main`.

## What to do when stuck

1. Re-read the relevant doc (`ARCHITECTURE`, `AGENTS`, or `DATA`).
2. If the doc is wrong, update the doc *and* the code in the same commit.
3. If you genuinely don't know, stop and surface the question — don't guess and ship.

## What done looks like

- `https://sankalp-xxxxx-as.a.run.app` returns 200 on `/api/healthz` (bare `/healthz` is reserved by Google Frontend on `*.run.app`)
- The chat UI streams a four-stage response for the demo input
- The Form 6 PDF generation produces a valid PDF
- The StoryAgent renders a constituency narrative end-to-end
- The README has the live URL filled in
- The smoke test passes
- The repo is under 10 MB, single branch, public

That's the bar. Hit it.
