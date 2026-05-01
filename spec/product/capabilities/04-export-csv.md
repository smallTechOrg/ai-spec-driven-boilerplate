# Capability 04 — Export Leads as CSV

**What it does:** Streams the currently filtered leads view as CSV.

**Inputs:** Same query params as `/leads`: `country`, `industry`, `size_band`, `min_score`.

**Outputs:** CSV response with `Content-Disposition: attachment; filename="leads.csv"`.

**Columns:** `name, website, country, industry, size_band, hq_city, score, rationale, description`.

**External calls:** Postgres via repository only.

**Error cases:** If the query fails, render the error page (never raw JSON — per code-style rule).

**Success criteria:** Golden-path smoke test downloads CSV, asserts header row and at least one data row.
