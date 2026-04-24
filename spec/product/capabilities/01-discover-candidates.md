# Capability 01 — Discover SMB Candidates

**What it does:** Given (country, industry, size_band), returns a list of candidate SMB URLs + snippets via a pluggable `SearchTool`.

**Inputs:** `Filters(country, industry, size_band)`.

**Outputs:** `list[dict]` — each `{title, url, snippet}`.

**External calls:** DuckDuckGo HTML search (v0.1). `SearchTool` protocol allows swap for Apollo/Clearbit later.

**Error cases:**
- Network timeout → logged, returns empty list, run continues and completes with 0 leads.
- Zero results → run completes with 0 leads (no error).

**Success criteria:** Phase 3 end-to-end test — searching `Germany Manufacturing 11-50` returns ≥5 URLs from DuckDuckGo.
