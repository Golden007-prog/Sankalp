# Product Requirements

What Sankalp is for, who uses it, and how we know it's working.

---

## 1. The problem

The Election Commission of India runs voters.eci.gov.in for 970+ million voters. The portal works, but it's a directory of seven disconnected forms and lookups, not a journey. To register, a first-time voter must:

1. Find the right form (Form 6 vs 8 vs 6A — not obvious)
2. Read instructions in English or Hindi only (real coverage of regional languages is patchy)
3. Fill in fields that map to legal categories (relation type, AC code) without context
4. Find their Assembly Constituency code from a separate lookup
5. Find their polling booth from another lookup
6. Track their application status from a third lookup

Each step is a drop-off point. Most first-time voters bounce after step 3.

The data is public. The fragmentation is the problem.

## 2. Who Sankalp is for

Three primary personas. The product decisions trace back to these.

### 2.1 Riya, 19, first-time voter

Bengaluru South, B.Com first year. Trilingual (Kannada-Hindi-English) but writes only English fluently. Lives with parents, will move to Mumbai for a job in 8 months. Has never filled a government form. Wants to vote in the next state election but isn't sure if she's registered, or how to update her address when she moves.

**What Sankalp does for Riya:** voice-first registration in Kannada, automatic address pre-fill from PIN, guidance on Form 8 (address change) when she moves.

### 2.2 Ravi Kumar, 62, retired bank clerk

Patna outskirts. Native Bhojpuri/Hindi speaker. Limited English. Has voted in every election since 1985 but his EPIC card is from 1998 and the photo is unrecognizable. Mild diabetic neuropathy — finds typing on phones difficult. Voted at a school 1.2 km away last time but has heard the booth may have changed.

**What Sankalp does for Ravi:** voice-first verification in Hindi, photograph the old EPIC and auto-fill Form 8 (replacement EPIC + photo update), confirm current booth assignment with directions in walking-friendly mode.

### 2.3 Priya, 28, software engineer

Hyderabad. Telugu-English bilingual. Tech-confident. Voted twice. Politically engaged, follows local issues. Wants to share constituency-level information with friends to encourage them to vote.

**What Sankalp does for Priya:** the civic narrative ("Why YOUR vote matters") with shareable permalink, accessibility features she can recommend to her parents, the booth-finder she uses on election morning.

### 2.4 Out of scope

NRI voters (Form 6A flow exists but isn't built for this hackathon). Service voters. Voters under 17 (we surface pre-registration but don't optimize for it).

## 3. The seven user journeys

Each journey is a sequence of agent invocations. All start at the Orchestrator.

### 3.1 First-time registration (Form 6)

**Trigger:** "I want to register to vote" (any language).

```
Orchestrator (lang detect, intent=register)
  → RegistrationAgent
      → ask name (English + native script)
      → ask DOB (auto-validate 18+)
      → ask gender
      → ask father/mother name
      → ask address (house, street, city, state, pin)
      → pin_to_constituency → confirm AC
      → ask mobile (optional)
      → ask disability_status (optional)
      → summarize all fields → confirm
      → generate Form 6 PDF → return signed URL
  ← Orchestrator (offer next step: "find your booth?")
```

**Time budget:** under 5 minutes for an attentive user.

**Success criteria:** PDF downloads correctly, fields render in the form's printable layout, EPIC submission flow on voters.eci.gov.in works with the generated PDF.

### 3.2 EPIC verification by number

**Trigger:** "Am I on the voter list? My EPIC is ABC1234567."

```
Orchestrator (intent=verify)
  → VerificationAgent
      → epic_search(epic_number)
      → if found → summarize record + offer corrections
      → if not found → disclose mock data scope, suggest registration
  ← Orchestrator (offer booth lookup or story)
```

**Time budget:** under 30 seconds.

### 3.3 EPIC verification by photo

**Trigger:** user taps camera icon, photographs old EPIC card.

```
Frontend (camera capture) → POST /vision/epic
  Backend → Cloud Vision OCR → parse_epic_ocr → SessionState.last_ocr
Frontend → POST /chat with "verify this card"
  Orchestrator (intent=verify, sees last_ocr)
    → VerificationAgent
        → epic_search(parsed fields)
        → diff old EPIC vs current record → suggest_corrections
        → offer Form 8 hand-off
    ← Orchestrator
```

**Time budget:** under 1 minute including OCR.

### 3.4 Address change (Form 8)

**Trigger:** "I moved to a new address. How do I update my voter ID?"

```
Orchestrator (intent=register, change_type=address)
  → RegistrationAgent (Form 8 flow)
      → ask EPIC number (or pull from session)
      → ask new address fields
      → pin_to_constituency on new pin → flag if AC changes
      → if AC changes: explain that this needs a fresh registration,
        not a Form 8, in the new constituency
      → generate Form 8 PDF
  ← Orchestrator
```

**Time budget:** under 4 minutes.

### 3.5 Polling booth lookup

**Trigger:** "Where do I vote?"

```
Orchestrator (intent=booth)
  → BoothAgent
      → resolve via session.last_voter_record OR ask EPIC/PIN
      → lookup_booth → get_accessibility → get_directions
      → render BoothCard with map + accessibility chips
  ← Orchestrator (offer story)
```

**Time budget:** under 30 seconds.

### 3.6 Civic narrative (the demo moment)

**Trigger:** "Why does my vote matter?" or tap on the story CTA.

```
Orchestrator (intent=story)
  → StoryAgent
      → resolve ac_code
      → fetch constituency + turnout + margin history
      → compose 200-word narrative in user's language
      → user opts in for cover → imagen_cover
      → user opts in for audio → tts_narrate
      → store_story → return permalink
  ← Orchestrator (offer share or next action)
```

**Time budget:** under 20 seconds for text, plus 5–10 sec each for cover and audio if requested.

### 3.7 Language switch mid-flow

**Trigger:** user types something in a different language at any point.

```
Every Orchestrator turn:
  → detect_language → if changed, update session, acknowledge in one
    sentence, continue current flow in new language
```

**No flow interruption.** This is the most-tested invariant.

## 4. Non-goals (deliberate)

- **No login, no account.** Anonymous sessions, opaque IDs. This protects users and simplifies privacy.
- **No real form submission to ECI.** We generate PDFs the user submits. Trust boundary.
- **No live electoral roll integration.** Mock data, disclosed in-app and in DATA.md.
- **No political content.** Sankalp is process help, not opinion. Candidate names, party preferences, voting recommendations are all explicitly out of scope.
- **No WhatsApp bot in v1.** Web-first. WhatsApp is a v2 distribution play.
- **No native mobile apps.** PWA via Next.js. Mobile web is the target.

## 5. Functional requirements

### 5.1 Multilingual support

| Language | Status at launch | Native script | Voice |
|---|---|---|---|
| English | ✓ | Latin | ✓ |
| Hindi | ✓ | Devanagari | ✓ |
| Bengali | ✓ | Bengali | ✓ |
| Tamil | ✓ | Tamil | ✓ |
| Kannada | ✓ | Kannada | ✓ |
| Telugu | ✓ | Telugu | ✓ |
| Marathi | ✓ | Devanagari | ✓ |
| All other 22nd Schedule languages | post-hackathon, ~1 day each | varies | varies |

Gemini handles all 22 natively. The constraint is UI strings (handled with a JSON i18n bundle) and TTS voice availability.

### 5.2 Multimodal input

**Text.** Required. Standard chat input.
**Voice.** Required. Push-to-talk via browser microphone, streamed to Gemini Live API. Max 5-minute session.
**Camera.** Required. EPIC card photo via `<input capture="environment">`. JPEG, max 5 MB, parsed via Cloud Vision OCR.
**File upload.** Optional. PDF or image of an existing voter document. Same OCR path.

### 5.3 Accessibility

- WCAG 2.1 AA contrast across all UI states.
- Screen-reader labels on every interactive element.
- All form fields available via voice (typing is never the only path).
- Keyboard navigable (Tab order, Enter to send, Esc to close modals).
- Font sizing scales from 14px base to 22px in "large text" mode (top-bar toggle).
- Color is never the only signal (status icons + text always paired).

### 5.4 Performance

- First contentful paint under 1.5s on 4G mobile (Lighthouse).
- Time to first SSE chunk under 2.0s on the chat endpoint (warm).
- Cold start (Cloud Run min-instances=1 keeps this rare): under 5s.
- Story generation end-to-end (text only): under 20s.

### 5.5 Reliability

- Backend uptime target during demo window: 99% (acceptable for hackathon).
- Graceful degradation paths defined for: Gemini timeout, Firestore unavailable, Maps quota, Vision OCR failure, Imagen quota. Documented in `ARCHITECTURE.md` §12.

## 6. Success metrics

These are the numbers we'd track if Sankalp went live. For the hackathon, they're aspirational benchmarks for the demo.

| Metric | Definition | Target |
|---|---|---|
| Activation | % of sessions that complete at least one of: register, verify, booth, story | 60% |
| Form 6 completion rate | % of users who start registration and download a PDF | 70% |
| Voice usage | % of sessions using voice input at any point | 25% |
| Camera usage | % of sessions using camera input | 10% |
| Median language | Most common UI language | Hindi |
| Story share rate | % of story sessions that copy the permalink | 15% |
| Cost per session | Total Vertex AI + Maps + Imagen + TTS | under $0.05 |

For the hackathon specifically, the demo metrics that matter:
- One end-to-end happy path through all four specialists in one session.
- Three languages demonstrated (English, Hindi, one regional).
- Voice + camera + text all triggered at least once in the demo recording.
- The story narrative renders for at least three different constituencies cleanly.

## 7. Risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| voters.eci.gov.in changes form layouts mid-build | medium | medium | We use ECI-published Form 6/8 PDF templates from gazette notifications, not the website's layout |
| Mock data feels too obviously fake | low | medium | Use real constituency names + real historical results from ECI Statistical Reports — only voter records are synthetic |
| Gemini Live API rate-limited during demo | low | high | Fall back to traditional STT (Web Speech API) for voice |
| Imagen content filter rejects civic prompts | low | low | Pre-test prompts; have text-only fallback |
| Judge can't reproduce locally | medium | medium | Comprehensive DEPLOYMENT.md, env.example, smoke test |
| Cold start kills first impression | medium | high | min-instances=1 on backend during judging window |
| 10 MB repo size limit hit | low | medium | Don't commit `.next/`, `node_modules/`, mock voter data >2 MB. Pre-commit hook enforces. |

## 8. Open product questions for the build

1. **Should we let users save and resume their Form 6 session via a magic link?** Probably yes (low effort, high value). Defer to v1.1 if time tight.
2. **Should we offer a "share with my parent" deeplink that pre-fills the language?** Yes if time allows — high virality lever for the senior persona.
3. **Should the story narrative cite its sources inline, or footnote them?** Footnote, expandable. Citation discipline matters for trust.
4. **Should we tag stories with a "verified by ECI Statistical Report XX/YYYY" badge?** Yes — strengthens trust and is honest about the data origin.

## 9. What "ready to ship" means

For the hackathon submission specifically:

- README with live Cloud Run URL filled in
- All seven journeys reachable via the chat UI
- The four specialists demonstrably working (smoke test passes)
- The story narrative renders cleanly for three different constituencies
- At least three languages tested (recordings or screenshots)
- Repo under 10 MB, single branch, public
- Submission form filled with: GitHub URL, Cloud Run URL, vertical = Election Process Education

That is the minimum. Beyond that — a recorded demo video, a Looker Studio cost dashboard, a 3-slide pitch deck — strengthens the submission but isn't required.
