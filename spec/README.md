# spec — the goal

This directory is the human-authored **goal**: what the system should be. It is the
contract; `src/` conforms to it, and the analyst checks that `logs/` reconciles with it.
When spec and code disagree, the spec wins — fix the code (unless the spec itself is
wrong; then amend the spec first).

The **designer** authors this with the user, to the line level, during intake
(`harness/roles/designer.md`). The method that governs it lives in `harness/`.

## Structure

```
spec/
  product/            ← WHAT the system does (human-authored)
    01-vision.md
    02-architecture.md
    capabilities/     ← one file per discrete capability
    04-data-model.md
    05-api.md
    06-ui.md
    07-agent-graph.md ← required for any agent-framework project
  engineering/        ← HOW this build is done (editable defaults)
    tech-stack.md     ← chosen stack (default: Python/LangGraph + Next.js + SQLite/DuckDB + Claude)
    code-style.md
```

## Status

If `spec/product/01-vision.md` still contains `<!-- FILL IN -->` markers, intake is not
done — the designer must complete the spec (no placeholders) and designer + engineer +
qa must sign off before any code is written (`harness/method/lifecycle.md`).

## Governance

1. Spec before code — no `src/` change without a backing `spec/` change.
2. One fact, one place — cross-reference, don't duplicate.
3. Capabilities are atomic — one discrete thing per file.
4. WHAT in `product/`, HOW in `engineering/` — no implementation detail in product.
