PORT      ?= 8001
# GOAL/FOLLOWUP trace to the P1 EARS line (spec/capabilities/triage-ticket.md) — the SAME line as
# agent/gate_eval.py's CRITERION. DEMO check 6 judges the answer to GOAL against that CRITERION.
GOAL      ?= Please triage this support ticket and draft a reply: 'I was charged twice for my subscription this month and I am really frustrated. When will I get my money back?'
FOLLOWUP  ?= Can you make the reply a bit more apologetic?
DATA_FILE ?=                              # UNSET — this is a key-free/own-data agent (the ticket arrives in `goal`,
                                          # not as an uploaded resource), so no session fixture is sent.

.PHONY: setup dev gate demo-gate prod-gate

setup:
	cd ui && npm install
	uv run playwright install chromium

dev:
	trap 'kill 0' INT; python -m agent & cd ui && npm run dev

demo-gate: gate            # alias
gate:
	python -m agent.eval_lint                                      # 1 — [@eval] lint: every EARS line bound
	uv run pytest -q                                              # 2 — suite (real key, loose asserts) + Playwright
	@DATA_FILE="$(DATA_FILE)" bash scripts/demo_gate.sh $(PORT) "$(GOAL)" "$(FOLLOWUP)" # 3-8 — boot, health, two-turn, judge, UI, traces

# PROD gate (for /deploy) — DEMO + Postgres + artifact + reachable URL + no-secret-leak.
PG_URL ?= postgresql+asyncpg://localhost/agent_gate_test
IMG    ?= support-triage-agent:gate
URL    ?= http://localhost:8001
prod-gate: gate
	APP_DATABASE_URL="$(PG_URL)" uv run pytest -q
	docker build -t $(IMG) . || langgraph build -t $(IMG) .
	@bash scripts/prod_gate.sh "$(URL)"
	@! git grep -nE 'sk-[A-Za-z0-9]|APP_LLM_API_KEY=[^$$]' -- ':!*.md' \
	  || { echo "FAIL: secret in tracked files"; exit 1; }
