# Capability 02 — Extract Firmographics

**What it does:** Uses the LLM to turn raw search hits into structured `Candidate` records with name, website, HQ city, short description.

**Inputs:** `search_results: list[dict]`, plus the run's filter context for disambiguation.

**Outputs:** `list[Candidate]`.

**External calls:** `LLMClient.complete(prompt)` with `<node:extract>` tag.

**Error cases:**
- LLM returns malformed output → logged, that hit is skipped; node continues with the remainder.
- Zero parseable candidates → `candidates=[]`, run completes with 0 leads.

**Success criteria:** Stub-mode returns 3 article-shaped candidates; integration test asserts candidate count > 0.
