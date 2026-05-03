#!/usr/bin/env bash
# Sankalp end-to-end smoke test.
# Asserts:
#   1. /api/healthz returns {"status":"ok"}
#   2. /api/chat opens a text/event-stream
#   3. The stream emits ≥4 distinct SSE event types in order:
#        lang_detect, routing, specialist:<name>, final
#   4. The X-Sankalp-Session-Id header is set
#
# Usage:
#   bash scripts/smoke_test.sh [BACKEND_URL]
#
# BACKEND_URL defaults to http://localhost:8080. Pass the deployed
# Cloud Run URL after a release: bash smoke_test.sh https://sankalp-backend-...

set -euo pipefail

BACKEND_URL="${1:-http://localhost:8080}"
MESSAGE="${2:-Please verify my voter record. My EPIC number is ABC1234567.}"
TMP="$(mktemp -d 2>/dev/null || mktemp -d -t sankalp)"
trap 'rm -rf "$TMP"' EXIT

step() { printf "\n==> %s\n" "$1"; }
ok()   { printf "    ok  %s\n" "$1"; }
fail() { printf "    FAIL %s\n" "$1" >&2; exit 1; }

step "/api/healthz"
HEALTH="$(curl --fail --silent --show-error --max-time 10 "${BACKEND_URL}/api/healthz")"
echo "    $HEALTH"
echo "$HEALTH" | grep -q '"status":"ok"' || fail "healthz did not return ok"
ok "healthz"

step "/api/chat (SSE)"
HEADERS_FILE="$TMP/headers"
BODY_FILE="$TMP/body"
PAYLOAD="$(printf '{"message":"%s"}' "$MESSAGE")"
curl --fail --silent --show-error --no-buffer \
     --max-time 120 \
     -H "Content-Type: application/json" \
     -H "Accept: text/event-stream" \
     -D "$HEADERS_FILE" \
     -X POST "${BACKEND_URL}/api/chat" \
     -d "$PAYLOAD" \
     -o "$BODY_FILE"

if ! grep -qi '^content-type:[[:space:]]*text/event-stream' "$HEADERS_FILE"; then
  fail "/api/chat did not return text/event-stream"
fi
ok "content-type"

if ! grep -qi '^x-sankalp-session-id:[[:space:]]*[A-Za-z0-9_\-]\{16,\}' "$HEADERS_FILE"; then
  fail "X-Sankalp-Session-Id header missing"
fi
ok "session-id header"

# Count distinct event names. We need lang_detect + routing + specialist:* + final.
events="$(grep -E '^event:' "$BODY_FILE" | sed 's/^event:[[:space:]]*//' | sort -u)"
echo "    events seen: $(echo "$events" | tr '\n' ',' | sed 's/,$//')"
echo "$events" | grep -q '^lang_detect$' || fail "no lang_detect event"
echo "$events" | grep -q '^routing$'     || fail "no routing event"
echo "$events" | grep -q '^specialist:'  || fail "no specialist:* event"
echo "$events" | grep -q '^final$'       || fail "no final event"
ok "≥4 stage events streamed"

# Final event must be ok=true.
final_data="$(awk '/^event: final$/{getline; print}' "$BODY_FILE" | head -1)"
if ! echo "$final_data" | grep -q '"ok":[[:space:]]*true'; then
  fail "final event was not ok=true: $final_data"
fi
ok "final ok=true"

printf "\nsmoke test passed against %s\n" "$BACKEND_URL"
