# Spec-Driven Development

The spec is written before the code. No exceptions.

## Why

When code is written without a spec, parts of the system make inconsistent assumptions,
testing becomes guesswork, every AI session re-derives requirements, and scope creeps
silently. When the spec comes first, every session reads the same requirements, tests
derive from the spec, and "does this match the spec?" is a concrete, answerable question
the analyser can audit.

## What goes where

- **`spec/product/`** — WHAT the system does: behavior, users, data, APIs, UI.
- **`spec/engineering/`** — HOW this build is done: chosen stack, code style, project rules.
- **Not in the spec** — line-by-line implementation (that's `src/`), temporary
  workarounds, or session notes (those go in `logs/sessions/`).

## When requirements change

1. Write a **CR as a delta** (ADDED / MODIFIED / REMOVED) against the existing spec —
   not a fresh spec. (`harness/process/templates/CR.md`.)
2. Update `src/` to satisfy the delta.
3. **Archive/merge:** when the CR lands, fold its delta back into the FR/spec baseline so
   `spec/` reflects current reality, and mark the CR `done`.
4. The analyser confirms `logs/` reconciles with the amended baseline.

### The archive/merge step is load-bearing

This is the step every competing SDD tool skips, and it is exactly where reconciliation
breaks: if an applied CR is never merged into the baseline, `spec/` slowly stops describing
the system, and "does the code match the spec?" becomes unanswerable. **A reconciliation
rule with no enforced merge + check is just a wish.** The merge is mandatory, not optional;
the analyser's drift check (see [observability.md](../patterns/observability.md)) verifies it
held.


## Spec vs. implementation conflicts

If the spec says X and the code does Y, the code is wrong — fix it. Exception: if the
spec itself is wrong, amend the spec (researcher + reviewer) first, then fix the code.
The analyser may *propose* spec amendments when outcome diverges from goal; the human and
reviewer approve them. The analyser never silently edits the goal.


## Exceptions

User's intention is supreme, and they should always be override this, by allowing spec to be generated from code. But make sure to ask them for explicit permission.

One such case is a brownfield codebase, in that case it is necessary to generate spec from the existing code and from that point onwards user can switch to spec driven development. Or in a case when the user is technically proficient, and they know the code they are changing.



