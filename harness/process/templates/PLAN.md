# PLAN — Phase <N>: <theme>

> **Single hardcoded coordination path** (`logs/PLAN.md`). Rewritten whole at the start of
> each phase, scoped to ONE phase. Carries NO formal requirements — those live in `spec/`.
> Every sub-agent opens this exact path without being told its name; each updates only its own
> tracker row. The planner truncates-and-rewrites this file when a new phase begins.

**Realising:** `spec/delivery-plan.md` Phase <N> criteria P<N>-AC1..P<N>-ACm  
**Session log:** `logs/sessions/<file>`  ← supervisor fills this back-pointer when it opens the phase  
**Status:** planning | building | review | accepted

---

## Step DAG

> The planner's parallel work-unit slice of THIS phase. Step 0 = scaffold (first phase only);
> subsequent phases start at the first delta step.

| # | Deliverable | Depends on | Parallel group | Gate command | Est. |
|---|-------------|------------|----------------|--------------|------|
| 0 | <!-- scaffold (first phase only) --> | — | — | `<gate>` | |
| 1 | <!-- step --> | | | | |

---

## Progress Tracker

> One row per step. Every agent updates its OWN row on handoff.
> Status: `todo → in-progress → gate-green → accepted`.
> `accepted` is set only at the phase boundary when the user accepts the phase.

| Step | Status | Gate output (session ref) | Reviewer sign-off | Dominant cost |
|------|--------|---------------------------|-------------------|---------------|
| 0 | todo | — | — | — |

---

## Phase Acceptance

> The gate checklist result for the phase + traceability back to `spec/delivery-plan.md`
> P<N>-ACn coverage. Reviewer writes pass/fail here; supervisor records user acceptance here.

| P<N>-ACn | Covered by step(s) | Reviewer verdict | Evidence (session ref) |
|----------|--------------------|------------------|------------------------|
| P<N>-AC1 | | pass / fail | |

**Reviewer sign-off:** <!-- pass / fail + one line -->  
**User acceptance:** <!-- accepted on YYYY-MM-DD HH:MM — or "pending" -->
