#!/usr/bin/env bash
# DEMO gate: check 0 (README) + checks 3-8 (1 = eval_lint, 2 = pytest run before this). Exit 0 = done.
set -euo pipefail
PORT="${1:-8001}"
GOAL="${2:-Please triage this support ticket and draft a reply: 'I was charged twice for my subscription this month and I am really frustrated. When will I get my money back?'}"
FOLLOWUP="${3:-Can you make the reply a bit more apologetic?}"
BASE="http://localhost:${PORT}"
: "${APP_LLM_API_KEY:?fund a key for a real run}"        # no key -> no gate

# 0 — README is a REQUIRED deliverable (build.md §3): it exists and documents the owner-facing gate entry point.
[ -f README.md ] || { echo "FAIL: README.md is missing (a REQUIRED deliverable — build.md §3)"; exit 1; }
grep -q 'make gate' README.md \
  || { echo "FAIL: README.md does not document \`make gate\` — the gate entry point an owner runs"; exit 1; }

# 3 — boot the server in the background, ensure we kill it on any exit
python -m agent & SERVER=$!
trap 'kill "$SERVER" 2>/dev/null || true' EXIT

# 4 — wait up to 30s for /health 200
for i in $(seq 1 30); do
  if curl -fsS "${BASE}/health" >/dev/null 2>&1; then break; fi
  sleep 1
  [ "$i" = 30 ] && { echo "FAIL: /health never came up"; exit 1; }
done
curl -fsS "${BASE}/health" | grep -q '"ok": *true' || { echo "FAIL: /health not ok"; exit 1; }

# 5 — TWO-TURN run on one session. Q1 then a follow-up Q2; ANY Q2 error fails the gate.
# This is a key-free/own-data agent (the ticket arrives in `goal`, no resource upload) — both turns send
# just {goal, session_id}; DATA_FILE stays UNSET.
DATA_FILE="${DATA_FILE:-}"
SID="gate-$(date +%s)"
Q1_PAYLOAD="$(jq -n --arg g "$GOAL" --arg s "$SID" '{goal:$g, session_id:$s}')"
if [ -n "$DATA_FILE" ]; then
  [ -f "$DATA_FILE" ] || { echo "FAIL: DATA_FILE=$DATA_FILE not found — generate a fixture for a session-scoped agent (build.md §3)"; exit 1; }
  Q1_PAYLOAD="$(jq -n --arg g "$GOAL" --arg s "$SID" --rawfile d "$DATA_FILE" '{goal:$g, session_id:$s, data:$d}')"
fi
R1="$(curl -fsS -X POST "${BASE}/runs" -H 'content-type: application/json' -d "$Q1_PAYLOAD")"
echo "$R1" | jq -e '.ok == true and .data.status == "completed"' >/dev/null \
  || { echo "FAIL: Q1 did not complete: $R1"; exit 1; }
RUN_ID="$(echo "$R1" | jq -r '.data.run_id')"
R2="$(curl -fsS -X POST "${BASE}/runs" -H 'content-type: application/json' \
      -d "$(jq -n --arg g "$FOLLOWUP" --arg s "$SID" '{goal:$g, session_id:$s}')")" \
  || { echo "FAIL: Q2 (follow-up on same session) errored"; exit 1; }
echo "$R2" | jq -e '.ok == true and .data.status == "completed"' >/dev/null \
  || { echo "FAIL: Q2 did not complete on the same session: $R2"; exit 1; }

# 6 — outcome (judge-stable, multi-sampled) + trajectory eval on the Q1 run
python -m agent.gate_eval --run-id "$RUN_ID" --goal "$GOAL" \
  || { echo "FAIL: outcome eval (below threshold-with-margin or high judge variance; trajectory is advisory)"; exit 1; }

# 7 — UI journey (skip with UI_E2E=0 for a headless product). Auto-skip with a printed reason if ui/ was never scaffolded.
if [ "${UI_E2E:-1}" = "1" ]; then
  if [ ! -d ui/node_modules ]; then
    echo "SKIP check 7: ui/node_modules absent. Run \`make setup\` (cd ui && npm install + uv run playwright install chromium) to enable."
  else
    uv run playwright install chromium >/dev/null 2>&1 || true   # idempotent; ensure the browser binary exists
    ( cd ui && npm run dev >/tmp/triage_ui_dev.log 2>&1 & echo $! >/tmp/triage_ui_dev.pid )
    trap 'kill "$SERVER" 2>/dev/null || true; [ -f /tmp/triage_ui_dev.pid ] && kill "$(cat /tmp/triage_ui_dev.pid)" 2>/dev/null || true' EXIT
    for i in $(seq 1 30); do curl -fsS "http://localhost:3001" >/dev/null 2>&1 && break; sleep 1; done
    uv run pytest tests/e2e/test_primary_journey.py -q \
      || { echo "FAIL: Playwright UI journey (post-JS DOM / console error)"; exit 1; }
  fi
fi

# 8 — traces present for the Q1 run. Grep the RUN_ID (rendered VERBATIM), NOT the goal text (it's _esc()'d).
curl -fsS "${BASE}/traces" | grep -q "$RUN_ID" \
  || { echo "FAIL: run $RUN_ID not visible at /traces"; exit 1; }

echo "DEMO GATE PASS"          # the only success signal is exit 0
