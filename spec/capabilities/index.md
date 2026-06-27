# Capabilities Index

## Capabilities in This Project

| Capability | File | Phase |
|------------|------|-------|
| File Ingest | [file-ingest.md](file-ingest.md) | Phase 1 |
| NL-to-SQL | [nl-to-sql.md](nl-to-sql.md) | Phase 1 |
| Insights (metrics, trends, anomaly detection + prose narrative) | [insights.md](insights.md) | Phase 1 |
| Charts (auto-selected chart specs rendered client-side) | [charts.md](charts.md) | Phase 1 |

## Notes

- All four capabilities ship in Phase 1 together — they form the indivisible primary user journey: upload → ask → see prose + charts.
- Caching (analysis_cache table) wires in Phase 2.
- PostgreSQL connectivity is deferred to Phase 4.
