#!/usr/bin/env bash
# Sankalp smoke test — Phase 0 placeholder.
# Phase 3 will extend this to assert the four-stage SSE stream.
set -euo pipefail

BACKEND_URL="${1:-http://localhost:8080}"

echo "==> /api/healthz"
curl --fail --silent --show-error "${BACKEND_URL}/api/healthz"
echo
echo "==> ok"
