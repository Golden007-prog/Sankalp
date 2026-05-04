#!/usr/bin/env bash
# Riya end-to-end happy path: Kannada → register → verify → booth → story.
# Walks the four core specialists in one continuous SSE-backed session.
#
# Usage:
#   bash scripts/riya_happy_path.sh [FRONTEND_URL]
#
# FRONTEND_URL defaults to the deployed Cloud Run frontend; pass another
# (e.g. http://localhost:3000) to test against a local dev server.

set -euo pipefail

FRONTEND_URL="${1:-https://sankalp-frontend-93037232246.asia-south1.run.app}"
TMP="$(mktemp -d 2>/dev/null || mktemp -d -t sankalp)"
trap 'rm -rf "$TMP"' EXIT

step() { printf "\n==> %s\n" "$1"; }
ok()   { printf "    ok  %s\n" "$1"; }
fail() { printf "    FAIL %s\n" "$1" >&2; exit 1; }

# ---- 1. Kannada-language register intent → RegistrationAgent route ----
step "1/4  Kannada register intent"
SESS_FILE="$TMP/session"
HDR_FILE="$TMP/hdr1"
BODY_FILE="$TMP/body1"
PAYLOAD='{"message":"ನಾನು ಮತದಾರನಾಗಿ ನೋಂದಾಯಿಸಬೇಕು","language":"kn"}'

curl --fail --silent --show-error --no-buffer \
     --max-time 120 \
     -H "Content-Type: application/json" \
     -H "Accept: text/event-stream" \
     -D "$HDR_FILE" \
     -X POST "${FRONTEND_URL}/api/proxy/chat" \
     -d "$PAYLOAD" \
     -o "$BODY_FILE"

SID="$(awk -F': ' 'tolower($1)=="x-sankalp-session-id"{gsub("\r","",$2); print $2}' "$HDR_FILE")"
[ -n "$SID" ] || fail "no session id from /api/proxy/chat"
echo "$SID" > "$SESS_FILE"
echo "    session: $SID"
grep -q '^event: lang_detect$' "$BODY_FILE" || fail "no lang_detect event"
grep -q '^event: routing$' "$BODY_FILE"     || fail "no routing event"
grep -q '^event: final$' "$BODY_FILE"       || fail "no final event"
ok "lang_detect + routing + final present"

# LLM routing for free-form intents is non-deterministic — Kannada
# "I want to register as a voter" can route either to RegistrationAgent
# or VerificationAgent (both reach the user's goal via different doors).
# Accept any specialist routing OR a registration/verification mention.
if grep -qE '^event: specialist:(registration|verification)_agent$' "$BODY_FILE" \
   || awk '/^event: final$/{getline; print}' "$BODY_FILE" \
       | grep -qiE 'form ?6|registration|register|verify|ನೋಂದಣಿ'; then
  ok "registration intent reached a specialist"
else
  fail "neither specialist routed nor registration mentioned in final"
fi

# ---- 2. Verify Riya's EPIC ----
step "2/4  Verify EPIC ABC1234567"
HDR_FILE="$TMP/hdr2"
BODY_FILE="$TMP/body2"
PAYLOAD="$(printf '{"message":"Verify my EPIC %s","session_id":"%s","language":"en"}' "ABC1234567" "$SID")"

curl --fail --silent --show-error --no-buffer --max-time 120 \
     -H "Content-Type: application/json" \
     -H "Accept: text/event-stream" \
     -D "$HDR_FILE" \
     -X POST "${FRONTEND_URL}/api/proxy/chat" \
     -d "$PAYLOAD" \
     -o "$BODY_FILE"

if awk '/^event: final$/{getline; print}' "$BODY_FILE" \
     | grep -q '"intent":[[:space:]]*"verify"'; then
  ok "intent=verify in final"
elif grep -q '^event: specialist:verification_agent$' "$BODY_FILE"; then
  ok "verification_agent specialist fired"
else
  fail "verify intent not surfaced"
fi

# ---- 3. Booth lookup ----
step "3/4  Booth lookup"
HDR_FILE="$TMP/hdr3"
BODY_FILE="$TMP/body3"
PAYLOAD="$(printf '{"message":"Where do I vote?","session_id":"%s","language":"en"}' "$SID")"

curl --fail --silent --show-error --no-buffer --max-time 120 \
     -H "Content-Type: application/json" \
     -H "Accept: text/event-stream" \
     -D "$HDR_FILE" \
     -X POST "${FRONTEND_URL}/api/proxy/chat" \
     -d "$PAYLOAD" \
     -o "$BODY_FILE"

if awk '/^event: final$/{getline; print}' "$BODY_FILE" \
     | grep -qE '"intent":[[:space:]]*"booth"|booth_card'; then
  ok "booth intent / booth_card marker"
elif grep -q '^event: specialist:booth_agent$' "$BODY_FILE"; then
  ok "booth_agent specialist fired"
else
  fail "booth intent not surfaced"
fi

# ---- 4. Story narrative ----
step "4/4  Story narrative"
HDR_FILE="$TMP/hdr4"
BODY_FILE="$TMP/body4"
PAYLOAD="$(printf '{"message":"Why does my vote matter?","session_id":"%s","language":"en"}' "$SID")"

curl --fail --silent --show-error --no-buffer --max-time 180 \
     -H "Content-Type: application/json" \
     -H "Accept: text/event-stream" \
     -D "$HDR_FILE" \
     -X POST "${FRONTEND_URL}/api/proxy/chat" \
     -d "$PAYLOAD" \
     -o "$BODY_FILE"

if awk '/^event: final$/{getline; print}' "$BODY_FILE" \
     | grep -qE '"intent":[[:space:]]*"story"|"story":'; then
  ok "story intent / story marker"
elif grep -q '^event: specialist:story_agent$' "$BODY_FILE"; then
  ok "story_agent specialist fired"
else
  fail "story intent not surfaced"
fi

printf "\nRiya happy path passed against %s (session %s)\n" "$FRONTEND_URL" "$SID"
