---
name: fix
description: Diagnose and fix a defect while keeping spec, code, and behavior reconciled. Use when something is broken or behaving wrong.
---

# fix

Run the Zer0 fix workflow. The authoritative procedure is `harness/workflows/fix.md` —
read it and follow it.

In brief: reproduce from `logs/` or a failing test; the **analyst** locates the
divergence and the **engineer** traces it; classify the drift (bug → fix `src/`; wrong
goal → designer amends `spec/` first); write a failing test, make it pass; qa signs off;
commit + push. The loop must close.
