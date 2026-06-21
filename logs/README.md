# logs/ — the outcome layer

What the system actually does. The third source of truth (`spec/` = intention,
`src/` = action, `logs/` = outcome). The analyser reads this layer to reconcile outcome
against goal. See [../harness/patterns/observability.md](../harness/patterns/observability.md).

```
logs/
  sessions/    build-time journals — one per working session (committed)
  runtime/     the built system's structured logs and traces (live data git-ignored)
  analysis/    the analyser's findings and reconciliation reports (committed)
```

- **sessions/** — `YYYY-MM-DD-HHMMSS-<branch>.md`. The ledger of *why* — decisions,
  gate results, open questions. Must exist before code is written; updated in real time.
- **runtime/** — the running system's logs. Live data is never committed (`*.log` is
  git-ignored); only fixtures/examples are.
- **analysis/** — the analyser's written output: drift findings and proposed `spec/`
  amendments for approval.
