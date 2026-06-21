# Spec-Driven Development

The spec is written before the code. No exceptions.

## Why

When code is written without a spec, parts of the system make inconsistent assumptions,
testing becomes guesswork, every AI session re-derives requirements, and scope creeps
silently. When the spec comes first, every session reads the same requirements, tests
derive from the spec, and "does this match the spec?" is a concrete, answerable question
the analyser can audit.

## What goes where

`spec/` holds exactly the seven phased product-spec docs — nothing else:

- **`spec/vision.md`** — WHY: the problem, users, success criteria (SC-N).
- **`spec/architecture.md`** — the system shape, components, failure/recovery model.
- **`spec/data-model.md`** — entities, schema, storage.
- **`spec/api.md`** — the endpoint contract (contract-first across all phases).
- **`spec/ui.md`** — what the interface IS, per phase.
- **`spec/agent-graph.md`** — the agent/node graph and its state.
- **`spec/delivery-plan.md`** — the durable phase roadmap: ordered phases, per-phase EARS
  criteria (`PN-ACn`), inter-phase deps. The phasing IS the roadmap — there is no separate
  ROADMAP file.
- **Not in the spec** — line-by-line implementation (that's `src/`), the live per-phase
  coordination state (that's `logs/PLAN.md`), or session notes (those go in `logs/sessions/`).

## When requirements change

There is no CR/FR delta file and no archive step. The phased spec docs are the single
baseline and are **edited in place**:

1. The researcher (with reviewer + human sign-off) **edits the affected `spec/` doc(s)
   directly** — add, modify, or remove the affected criteria, schema, endpoints, or screens.
   New scope that lands beyond the current phase becomes a **named later phase in
   `spec/delivery-plan.md`** (full `PN-ACn` EARS criteria), never a separate roadmap.
2. The planner rewrites `logs/PLAN.md` for the affected phase; executors update `src/` to
   satisfy the amended criteria.
3. The analyser confirms `logs/` reconciles with the amended baseline.

### Edit-in-place keeps the baseline true

This is the step every competing SDD tool skips, and it is exactly where reconciliation
breaks: if a change lands in `src/` with no backing edit in `spec/`, the spec slowly stops
describing the system, and "does the code match the spec?" becomes unanswerable. **A
reconciliation rule with no enforced spec edit + check is just a wish.** Every `src/` change
needs a backing edit in the phased spec docs; the analyser's drift check (see
[observability.md](../patterns/observability.md)) verifies it held — an applied change with
no backing spec edit is the silent reconciliation break.


## Spec vs. implementation conflicts

If the spec says X and the code does Y, the code is wrong — fix it. Exception: if the
spec itself is wrong, amend the spec (researcher + reviewer) first, then fix the code.
The analyser may *propose* spec amendments when outcome diverges from goal; the human and
reviewer approve them. The analyser never silently edits the goal.


## Exceptions

User's intention is supreme, and they should always be override this, by allowing spec to be generated from code. But make sure to ask them for explicit permission.

One such case is a brownfield codebase, in that case it is necessary to generate spec from the existing code and from that point onwards user can switch to spec driven development. Or in a case when the user is technically proficient, and they know the code they are changing.



