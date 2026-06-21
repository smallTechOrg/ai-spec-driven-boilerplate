# logs — the outcome

`logs/` is the third source of truth: what the system *actually does*. The **analyst**
owns this layer and reads it continuously (`harness/roles/analyst.md`).

## Structure

- `sessions/` — build-time journals, one per working session
  (`YYYY-MM-DD-HHMMSS-<branch>.md`). Required before any code is written
  (`harness/workflows/session-report.md`). Committed.
- `runtime/` — the built system's structured logs and traces. Live data is **not**
  committed (the `*.log` glob is git-ignored); only fixtures/examples are.
- `analysis/` — the analyst's findings and reconciliation reports: where the outcome
  (`logs/`) diverges from the goal (`spec/`), and the proposed adjustments. Committed.

## The loop

The analyst compares `logs/` (outcome) against `spec/` (goal). Drift → fix `src/`
(action) or propose a `spec/` amendment. See `harness/method/reconcile.md`.
