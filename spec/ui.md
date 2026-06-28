# UI — DataChat

---

## UI Type

A single-screen **browser workspace** (Next.js static export, Tailwind), served same-origin at `http://localhost:8001/app/`. One screen, three regions: a left **Library** rail, a center **Conversation** column, and a right **Inspector** (dataset profile + observability). Extends the existing `frontend/` skeleton in place (`frontend/src/app/page.tsx` + new components under `frontend/src/components/`).

> **Stub discipline:** in every phase, surfaces not yet wired are rendered as visible but clearly-labelled NON-FUNCTIONAL stubs (greyed, with a "Coming soon" badge) so the user sees the full vision and never mistakes a stub for a bug.

## Layout

```
┌──────────────┬───────────────────────────────┬───────────────────────┐
│  LIBRARY     │        CONVERSATION           │      INSPECTOR        │
│  (left rail) │        (center)               │      (right)          │
│              │                               │                       │
│  + Upload    │  [transcript of turns]        │  Dataset profile:     │
│  dataset list│   Q: ...                      │   columns / dtypes /  │
│              │   A: prose + key numbers      │   ranges / row count  │
│              │      ▸ Show code (panel)      │   quality flags       │
│              │      chart / table            │                       │
│              │      followup chips           │  Step timeline        │
│              │                               │  Tokens + cost        │
│  [multi-file]│  [ ask box ............ ]     │  Daily total          │
└──────────────┴───────────────────────────────┴───────────────────────┘
```

## Components & Phase Status

| Component | P1 | P2 | P3 | P4 |
|-----------|----|----|----|----|
| **Upload** (drag/drop CSV/Excel) | **real** | real | real | real |
| **Library list** (datasets) | stub (single in-session dataset shown) | **real** (persistent) | real | real |
| **Dataset profile panel** (columns, dtypes, ranges, row count) | **real** | real | real + flags | real |
| **Data-quality flag chips** | stub | stub | **real** | real |
| **Ask box** | **real** (single question) | real (multi-turn) | real | real |
| **Conversation transcript** (turn memory) | stub (one Q/A, no history) | **real** | real | real |
| **Answer card** (prose + key numbers) | **real** | real | real | real |
| **Collapsible code panel** ("Show code") | **real** | real | real | real |
| **Per-question token + cost** | **real** | real | real | real |
| **Step timeline** (planning → running → checking) | stub (static placeholder) | stub | **real** | real (live) |
| **Follow-up suggestion chips** | stub | stub | **real** (clickable) | real |
| **Chart** (interactive) | stub | stub | stub | **real** |
| **Pivot / summary table** | stub | stub | stub | **real** |
| **Token streaming** (token-by-token answer) | stub (renders whole answer at once) | stub | stub | **real** (SSE) |
| **Daily cost total** | stub | stub | stub | **real** |
| **Run-history browser** | stub | stub | stub | **real** |
| **Multi-file / folder picker** | stub | stub | stub | **real** |

## Key Interactions

- **Upload (P1):** drop/select a file → progress → on success the profile panel fills and the dataset becomes active. Errors (bad type, too big) show inline.
- **Ask (P1):** type a question → "Analyzing…" → answer card appears with the prose answer and key numbers; "Show code" expands the exact pandas that ran; token/cost shown under the card. P1 has no history — one Q/A at a time.
- **Multi-turn (P2):** the transcript accumulates turns and persists across reload; follow-ups depend on prior context.
- **Reasoning transparency (P3):** the step timeline animates through planning → running code → checking result; each step expands to its code; if the agent self-corrected, multiple code steps are visible. Ambiguous questions surface a clarifying prompt or a clearly-flagged assumption. Follow-up chips are clickable to ask them.
- **Rich output + live (P4):** answers may render an interactive chart or a pivot table; the answer streams token-by-token while the timeline updates live; the daily-cost total increments; the run-history browser lists past runs with their code/result/tokens/cost/timestamps; the multi-file picker lets the user select several files / a folder to analyze together.

## States to Handle

Empty (no dataset yet — invite upload), uploading, profiling, idle-with-dataset, analyzing, answer-ready, **answer-failed** (honest "couldn't compute" with the attempted code shown — not a crash), and uncertain (clarifying question / flagged assumption). Stubs always render in a visibly disabled "Coming soon" state.

## Accessibility / Polish

Keyboard-submit on the ask box, readable monospace for the code panel, copy-to-clipboard on code, and a clear visual distinction between a real surface and a "Coming soon" stub.
