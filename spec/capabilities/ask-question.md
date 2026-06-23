# Capability: Ask Question (NL → SQL → Narrative + Table)
## What It Does
Answers one natural-language question over a selected dataset by generating read-only SQL from schema + capped samples, running it locally on DuckDB, and returning a senior-analyst narrative plus a formatted result table.
## Inputs
| Input | Type | Source | Required |
|-------|------|--------|----------|
| dataset_id | string | `POST /ask` body | yes |
| question | string | `POST /ask` body | yes |
| session_id | string | `POST /ask` body | no |
## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| narrative | string | `POST /ask` response → Result view |
| sql, columns, rows (capped), row_count, duration_ms | JSON | `POST /ask` response → Result view |
| AuditLogRow | metadata row | SQLite (`audit_logs`) |
## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| Gemini (`gemini-2.5-flash`) | Generate SQL; narrate result | retry 2× → 502, audit `failed` |
| DuckDB | Execute the SELECT | 400/500, audit `failed` |
## Business Rules
- The LLM prompt for SQL generation contains schema + at most `AGENT_MAX_SAMPLE_ROWS` sample rows + small aggregates — never full rows.
- Only a single read-only SELECT is executed; non-SELECT or unknown-column SQL is rejected (400).
- The narrate step sees only a capped result preview, not the full result set.
- Every ask — success or failure — writes exactly one audit row.
## Success Criteria
- [ ] A factual aggregation question returns a table whose numbers match a direct DuckDB query.
- [ ] The outgoing SQL-generation prompt contains ≤ `AGENT_MAX_SAMPLE_ROWS` data rows (asserted by inspecting the prompt).
- [ ] Each ask produces exactly one `audit_logs` row with non-null `nl_question`, `generated_sql` (on success), `row_count`, `duration_ms`, `created_at`.
- [ ] A nonsensical question that yields invalid SQL returns 400 and an audit row with status `failed`.
- [ ] No request body or prompt to Gemini contains more than the capped sample rows (local-only constraint, asserted by test).
