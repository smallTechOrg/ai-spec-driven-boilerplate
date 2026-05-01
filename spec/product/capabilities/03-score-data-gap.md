# Capability 03 — Score Data-Maturity Gap

**What it does:** For each candidate, asks the LLM to estimate the likelihood (0–100) that the company lacks an in-house data function, with a one-sentence rationale.

**Inputs:** `list[Candidate]`.

**Outputs:** `list[Lead]` — each candidate plus `score` (0–100) and `rationale`.

**Rubric signals (given to the LLM in the prompt):**
- Size band (smaller → higher likelihood)
- Industry (manufacturing/retail/professional-services → higher likelihood than tech)
- Visible tech-stack poverty (old website, no careers page)
- Absence of data-role job postings mentioned on their site

**External calls:** `LLMClient.complete(prompt)` with `<node:score>` tag.

**Error cases:**
- LLM returns non-numeric score → default to 50, rationale = "score unparseable — manual review".
- Score out of 0–100 → clamp.

**Success criteria:** Integration test asserts every persisted lead has `0 ≤ score ≤ 100` and non-empty rationale.
