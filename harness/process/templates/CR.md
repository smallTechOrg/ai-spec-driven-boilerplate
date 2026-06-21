# CR-NNN — [Title]

**Date:** YYYY-MM-DD  
**Author:** [human / analyser]  
**Related:** FR-NNN or issue description  
**Status:** draft | approved | in-progress | done

> A CR is a **delta against an existing spec**, not a fresh spec. State the change as
> ADDED / MODIFIED / REMOVED below. When the CR lands, its delta is **folded back into the
> FR/spec baseline** (the archive/merge step in [spec-driven.md](../../rules/spec-driven.md))
> — that merge is what keeps spec and code reconciled. Skipping it silently breaks
> reconciliation.

---

## What Is Wrong / What Changed

> Describe the current behaviour and why it is incorrect or no longer acceptable.

<!-- One paragraph. Cite logs, error output, or the spec section that is violated. -->

## Spec Delta

> The precise change to the spec, as a diff. This is what gets merged into the baseline.

**ADDED**
- <!-- new EARS criterion or section -->

**MODIFIED**
- <!-- old → new. Quote the prior EARS line and the replacement. -->

**REMOVED**
- <!-- criterion/section no longer true -->

## Proposed Change

> What should be different in `src/` after this CR is applied? Be specific: which file,
> which behaviour, which output changes.

<!-- One paragraph. -->

## Success Criteria (EARS)

> How do we know the fix is complete? Each line is testable (same EARS forms as the FR).

- [ ] <!-- WHEN <trigger> the system SHALL <response> — the gate that was failing now passes -->
- [ ] <!-- The system SHALL show no regression in the existing suite -->
- [ ] <!-- The session report SHALL show the green gate output -->

## Risk & Rollback

> What could go wrong, and how do we undo it?

| Risk | Likelihood | Rollback |
|------|-----------|---------|
| | | |

## Non-Goals

> What this CR does NOT change.

- <!-- e.g. "Does not address performance — separate CR" -->

## Root Cause (if known)

<!-- Filled in by the analyser. What in spec/, src/, or logs/ caused this? -->
