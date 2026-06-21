# Session — 2026-06-22 04:14 — v2.2 autonomous harness hardening

> **Mode:** autonomous 60-min iteration loop. User mandate: make this the best zero-shot
> agent-building harness in the world — Sonnet High → great, Opus → mind-blowing. Rewrite spec/
> to highest technical standard. Make recipes GENERIC (currently data-chat-specific) so copy →
> run out of the box. Simulate building agents, find failures, fix harness + recipes, iterate.
> Do not stop. Do not ask.

## Durable plan (survives compaction — read this first on resume)

| # | Round | State | Notes |
|---|-------|-------|-------|
| 1 | Spec redesign (design+author+review+audit+coord) | **DONE** | wf_c45fb59f-fb8 — 7 spec docs authored (4-5/5), coord model decided |
| 2 | Recipes: audit + generify (de-data-chat, copy-and-run) | **DONE** | wb4ywy872 — generic `echo` slice, stub-default LLM, all 3 verify green |
| 3 | Apply: harmonize 7 spec docs to 5/5 + migrate harness FR→logs/PLAN.md + verify | **running** | wffd38et9 (background) |
| 4 | Simulate building 3 diverse agents end-to-end; capture what breaks | pending | needs R2+R3 |
| 5 | Fix harness + recipes from sim findings | pending | needs R4 |
| 6+ | Re-simulate → fix → raise bar until convergence | pending | loop |

## R1 OUTPUT — coordination model LOCKED (three files)
- **spec/delivery-plan.md** = durable phase roadmap (phases + PN-ACn EARS criteria + deps). Phasing IS the roadmap.
- **logs/PLAN.md** = THE live coordination hub — single HARDCODED path every sub-agent opens (replaces "FR is single trackable file"; solves timestamp-discovery failure). Current-phase Step DAG + Progress Tracker + Phase Acceptance. Planner rewrites whole per phase.
- **logs/sessions/<ts>.md** = narrative log + latency ledger only.
- "iteration" RETIRED → "phase". spec/ holds ONLY 7 product-spec docs. No features/, FR, CR, ROADMAP, proposed-FR.
- Deletions done: spec/README.md, spec/ROADMAP.md, spec/features/, templates/FR.md, templates/CR.md.
- Refs: logs/analysis/coord-model.md (migration plan), logs/analysis/spec-review-fixes.md (harmonization).

## R2 OUTPUT — recipes generified (LOCKED contract)
- Generic vertical slice: UI → API → LangGraph ReAct → ONE `echo` "[REPLACE ME]" tool → stub LLM → DB persist (Run row) → response. Zero business domain.
- **Canonical recipe contract (all recipes MUST match):** `GET /health`→{status,stub_mode}; `POST /api/run` {input}→{ok,data:{result,run_id}}; `GET /` + `POST /run` = built-in Jinja UI; port **8000**. Next.js frontend calls `/health` + `/api/run`.
- LLM: provider=`stub` default (no key, fully offline); real=`anthropic`/`claude-sonnet-4-6` behind optional `llm` extra. `APPNAME_` env prefix (placeholder), `appname`/`APPNAME` one find-replace rename.
- Both python recipes now share identical layout (src/api, src/agent, src/db, src/integrations + stubs); differ only in storage layer.
- **FIXED manually:** frontend ChatApp.js called `${API}/run` (HTML form) → corrected to `${API}/api/run` (the agents couldn't coordinate cross-recipe contract).
- Watch in sim: starlette+httpx TestClient deprecation warning (cosmetic); next bumped 15.3.3→15.5.19 (CVE fix); anthropic provider import-verified, not live-tested.

## Design decisions locked
- spec/ = highly-technical phased product specification. NO features/, NO ROADMAP.md, NO README in spec/.
- Phasing IS the embedded roadmap. Phase 1 = shaped first release (UI present), ~30-min ceiling.
- Patterns + rules live in harness/ only (already moved).
- Recipes must be GENERIC agent boilerplate, not data-chat. Copy → uv sync → run → green.

## Latency ledger
| Round | Start | End | Dur | Dominant cost |
|-------|-------|-----|-----|---------------|
| R1 spec redesign | 04:14 | — | — | model-latency (workflow) |
| R2 recipes generify | 04:14 | — | — | model-latency (workflow) |

## Trace
- 04:14 — launched R1 spec-redesign workflow (wf_c45fb59f-fb8).
- 04:14 — opened this session report; launching R2 recipes workflow next.
