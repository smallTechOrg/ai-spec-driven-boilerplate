# Workflow: Build

`researcher → planner → executor → reviewer → deployer → analyser ↺`

Takes a user brief from zero to a working, reviewed, **user-testable delivery** of a
**phase** of the spec — built as **parallel steps**. The pipeline is autonomous after the one
human-touch approval gate per phase.

---

## Vocabulary — phase vs step (read this first)

These two words used to be conflated; they are now distinct, and the distinction is the whole
point of this workflow.

- **Phase** = one **end-to-end, user-testable increment**. This is the unit the *user* accepts.
  A small build may be **one phase**; larger work is an ordered series of phases, each a slice
  the user can run and test. The old plans had ~9 "iterations" before the user could test
  anything; that was the bug. There is **one** user acceptance boundary **per phase**, at the
  phase boundary. The durable, ordered phase roadmap (with per-phase EARS criteria PN-ACn and
  inter-phase deps) lives in `spec/delivery-plan.md`.
- **Step** = a green-gated ~10–15 min work-unit *inside* the current phase (scaffold, a model, an
  endpoint, a node, a UI page, the wiring). Steps are the **parallel units** — independent steps
  run at once as a swarm. A step is tested and green, but it is **not** a user-acceptance point;
  only the phase boundary is.

So: the planner slices the **current phase** into a step DAG; executors run independent steps in
parallel; the reviewer's full gate + user acceptance happen **once per phase**, when the steps
converge into a testable whole.

---

## The pipeline is a swarm, not a queue

The arrow order above is a *dependency order*. The supervisor **runs it as a swarm**: wherever
steps are independent it spawns parallel executors and gathers at the phase gate (see
[supervisor.md](../agents/supervisor.md) → Swarm orchestration). In particular:
- intake research probes + `harness/patterns/` usage-spec reads run concurrently;
- independent **steps run as parallel executors** (separate worktrees / disjoint paths);
- the **frontend is a first-class step** — built alongside its backend data within the same
  phase, never bolted on at the end;
- review runs **one reviewer per dimension** in parallel; findings merge at the gate.

The **phase gate is the barrier** — fan steps out, then reconcile into a user-testable whole
before the gate closes. Parallel writers use separate worktrees or disjoint paths; one owner per
file.

## Blackboard — what each stage reads and writes

| Stage      | Reads                            | Writes                                              |
|------------|----------------------------------|-----------------------------------------------------|
| researcher | user's brief                     | the phased spec files (`spec/vision.md`, `architecture.md`, `data-model.md`, `api.md`, `ui.md`, `agent-graph.md`, `delivery-plan.md`), `harness/rules/` |
| planner    | `spec/`                          | `logs/PLAN.md` (Step DAG + seeded Progress Tracker) |
| executor   | `spec/`, `logs/PLAN.md`          | `src/`, `tests/`, recipe scaffold, `logs/PLAN.md` tracker row |
| reviewer   | `spec/`, `src/`, `tests/`        | acceptance tests, sign-off, `logs/PLAN.md` tracker row |
| deployer   | `src/`, config                   | local demo running, result, `logs/PLAN.md` tracker row |
| analyser   | `spec/`, `src/`, `logs/`         | `logs/analysis/`, spec amendment proposals          |

Sub-agents share no memory. Coordination is through durable artefacts on disk.

**`logs/PLAN.md` is the single trackable file** — a hardcoded path every sub-agent opens
without being told its name. The planner **rewrites it whole at the start of each phase**
(scoped to that ONE phase): the `## Step DAG`, the seeded `## Progress Tracker`, the header
naming which phase and which `spec/delivery-plan.md` PN-ACn criteria it realises, and the
`## Phase Acceptance` checklist. Every stage thereafter updates its own tracker row as control
passes back to the supervisor. `logs/PLAN.md` carries **no** formal requirements — those live
in `spec/`. The three coordination files split cleanly:
- the **session report** (timestamped, `logs/sessions/…`) holds the narrative log + latency
  ledger — the supervisor passes its path explicitly when it spawns each agent;
- **`logs/PLAN.md`** holds the live plan + status of the current phase;
- **`spec/delivery-plan.md`** holds the durable phase roadmap (ordered phases + PN-ACn).

---

## Stages

### 1. researcher — get the goal right

Runs the **draft-first** intake (`harness/process/agents/researcher.md`) — **one human
round-trip**, not two serial question rounds (that was the slow path: ~10 min to a signed spec):
- **Draft the full phased spec from the brief first**, filling every field with best-fit defaults
  and marking each non-obvious guess `[ASSUMPTION: …]`. Reserve `[NEEDS CLARIFICATION]` only for
  the rare architecture-changing unknown that can't be defaulted.
- Writes the phased spec files (`vision.md`, `architecture.md`, `data-model.md`, `api.md`,
  `ui.md`, `agent-graph.md`, `delivery-plan.md`) with **EARS criteria** (PN-ACn per phase in
  `delivery-plan.md`); picks the stack (DuckDB vs SQLite first-class, both local-first) with
  rationale, all in the draft. Deferred scope is written as **later phases in
  `spec/delivery-plan.md`**, not a separate roadmap.
- **One consolidated approval moment**: drafted spec + phasing + stack + API-key list + any
  blocking markers batched as ≤4 choices. Approve-or-adjust in a single turn.
- Records which keys are present (boolean) in the session report.

**Pre-code spec gate (reviewer):** before the planner starts, the reviewer checks the spec for
the four requirement-bug classes (wrong level of detail, ambiguity, conflict, incompleteness)
and any unresolved marker. Cheapest place to catch a defect. (See `reviewer.md`.)

**Gate (supervisor):** spec coherent, PN-ACn criteria testable, phasing approved, stack approved,
all keys identified, no open clarification markers. After sign-off the pipeline runs autonomously
through the current phase.

### 2. planner — slice the current phase into a parallel step DAG

Reads the spec and slices the **current phase** (the phase named in `spec/delivery-plan.md`,
realising its PN-ACn criteria) into **steps**, where each step:
- Has one deliverable (describable in one sentence)
- Has one fast gate command (runnable in under 30 seconds)
- Takes ~10–15 minutes of executor work

The plan is a **DAG, not a queue**: mark which steps are **independent** (run in parallel) and
draw the dependency edges for the rest. The goal is the *current phase* testable at the end of
the phase — scope each capability DOWN to ship it minimally; scope beyond this phase belongs to
a **later phase in `spec/delivery-plan.md`**, not dropped silently. The frontend step ships
alongside its backend step, not after.

**Always starts with (first phase):**
- Step 0: scaffold — `/health` returns 200 (~8 min)
- Step 1: first model + unit test (~12 min)

Subsequent phases start at the first delta step (no scaffold).

**Rewrites `logs/PLAN.md` whole** for this phase: the header (phase + the PN-ACn it realises +
the session-log back-pointer + status), the `## Step DAG`, the seeded `## Progress Tracker`
rows (one per step, status `todo`), and the `## Phase Acceptance` checklist. `logs/PLAN.md` is
the single hardcoded coordination path all sub-agents read and write — it carries the execution
plan + status for this ONE phase, never any formal requirement (those stay in `spec/`).

### 3. executor — one step at a time, many in parallel

Each executor implements **exactly one step** per invocation. Independent steps run as **parallel
executors** at once (separate worktrees / disjoint paths; one owner per file).

**Step 0 — scaffold, stack-conditional** (the planner names the recipe; see the selection table
in `planner.md`). Copying the *wrong* recipe is exactly how the slow build lost — the recipe must
match the approved stack:

1. Copy the **selected** recipe to the project root (the planner names it):
   - Relational / transactional → `harness/recipes/python-fastapi-sqlite/`
   - Analytics (CSV/Parquet/JSON) → `harness/recipes/python-fastapi-duckdb/`
   - (+ `harness/recipes/frontend-nextjs/` if the phase needs a UI)
2. Replace all `appname` / `APPNAME` occurrences with the project name
3. `uv sync --extra dev` — the slowest scaffold step (network). **Kick it off in the
   background the moment the stack is approved** (during planning) so it's warm before the
   executor needs it; do the `appname` replace and README edits while it runs. Don't serialise
   behind it.
4. Tables are created automatically at startup — `create_tables()` in the lifespan (both
   recipes; no migration step, no Alembic). See [gotchas.md](../../rules/gotchas.md) C-DUCKDB-VIEW.
5. Confirm `curl http://localhost:8001/health` returns 200 with `stub_mode: true`
6. **Update `README.md`** — name, one-line description, prerequisites, exact `uv sync` +
   run quickstart, `.env` setup. README is a Step-0 deliverable, never deferred (C-README).
7. Commit: `step-0: scaffold — /health green`

**Subsequent steps:**
- Write exactly what the step plan says — one model, one endpoint, one node, one tool, one page
- Write the test first (or alongside) — never skip it
- Run the step's fast gate command; show output in session report
- Commit: `step-N: [deliverable]`

**Per-step gate is fast and green; it is not user acceptance.** A step is "done" when its
sub-30s gate passes and the analyser confirms no drift on handoff. The heavy reviewer checklist
and user acceptance happen once, at the phase boundary (stage 4).

**On blocker:** three attempts, then route to fix workflow — do not hack around it.

**Python conventions:**
- `src/` holds all application code; `tests/` at root
- External calls sit behind a thin client in `src/integrations/`
- Stubs in `src/integrations/stubs/` — the build runs fully offline until the LLM step
- `APPNAME_LLM_PROVIDER=stub` must be the default until the LLM step

### 4. reviewer — guard the goal at the phase boundary

When the steps converge into a user-testable whole, the reviewer runs the full gate **once**
against the phase's PN-ACn criteria in `spec/delivery-plan.md` — this is the single heavy
checkpoint, not a per-step tax. The reviewer records sign-off in `logs/PLAN.md`'s
`## Progress Tracker` sign-off cells and writes the pass/fail result into its `## Phase
Acceptance` section.

**The fixed gate checklist** (the planner does not re-invent it; the reviewer runs it).
Every line is pass/fail — the phase is not deliverable if any applicable line fails:

1. Gate command run, **output shown** in the session report (not "should pass").
2. Tests green against the **production driver**; offline (`…=stub`, no key, no network).
3. Golden-path smoke asserts rendered **content**, not just a 200 status.
4. Live-server (backend): `python -m src` up; `curl /health` + one real API route → 200, **exit codes logged**.
4b. Live-UI (if the phase has a frontend): the **UI origin is started** (`npm run start`, not just
   `npm run build`) and `curl http://localhost:3000/` → 200 **with an expected rendered DOM string
   in the body**. `npm run build` exiting 0 is *not* this check — it prerenders, it does not load
   the page, so it misses SSR browser-API 500s ([C-SSR-BROWSER-API]). A green build with an unloaded
   UI is exactly how the `localStorage` 500 reached deploy. Curl the frontend port, never :8001.
5. Stub mode is visibly **banner-labelled** in any UI (C-STUB-BANNER).
6. **No carry-forward defect deferred a second time** — a flagged defect is fixed, not re-noted.
7. Evals pass at threshold (agent-behaviour criteria); README current.
8. Working tree clean and pushed; session report updated.

See [testing.md](../../rules/testing.md) for the full gate law and
[gotchas.md](../../rules/gotchas.md) for the referenced IDs.

### 5. deployer — spin up the user-testable demo

Once the phase is green, spin up the local demo so the user can test the phase increment:
- `uv run python -m src`
- Confirm `http://localhost:8001` serves a live response
- Log curl output in session report

Deploy to Render or other targets only when the user explicitly requests it.
Never deploy to production automatically.
Confirm all irreversible actions with the user before proceeding.

### 6. analyser — close the loop

The supervisor invokes the analyser **after every handoff back to it** — after each step
returns, not only at the phase boundary. Every pass writes a findings file to
`logs/analysis/`; an early-step pass confirms what is present and names what the next step
still owes, so a missing artefact surfaces one handoff later instead of at the gate. The
analyser **decides on the fly** (see analyser.md) — a one-line verdict when clean, a terminal
route when drift is unambiguous.

At each pass, check: does `src/` match the spec (the current phase's PN-ACn in
`spec/delivery-plan.md`)? Does `logs/PLAN.md`'s tracker match where `src/` actually stands? Do
logs match `src/`?

| Signal | Action |
|--------|--------|
| spec ≠ src | route back to executor |
| src ≠ logs | route to fix workflow |
| logs ≠ spec | fix src/ or propose spec amendment |
| all agree | continue; at the phase boundary, surface to user for acceptance |

**Done signal:** the user explicitly accepts the **phase** (the user-testable increment, tested)
at the phase boundary. Never self-declare done. Spec amendments go to supervisor + user for
approval before any change.

---

## Session report

Each stage appends to `logs/sessions/YYYY-MM-DD-HHMMSS-<branch>.md`.
Use the template at `harness/process/templates/SESSION.md`.

Per-stage required fields: stage name + start/end timestamp, decisions, trace, harness friction,
gate output, blockers, what is next.
