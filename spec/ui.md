# UI

A single-page web app (Next.js 15 + React 19, static export) served single-origin at `/app`.
One screen. Visually complete in Phase 1: the real working path PLUS clearly-labelled
non-functional stubs so the user sees the full vision and never mistakes a stub for a bug.

## Screen: Analyze (`frontend/src/app/page.tsx`)

### Real (Phase 1, functional)
1. **Header** — product title + one-line tagline: "Upload a CSV, ask a question, see the
   answer and the exact code it ran. Your data stays on your machine."
2. **Upload control** — file picker (accept `.csv`). On select → `POST /datasets` (multipart).
   On success show the filename, row count, and a small schema/preview chip strip. On error
   show human copy ("Couldn't read that file as a CSV").
3. **Question box** — a textarea + **Analyze** button, enabled once a dataset is uploaded.
   On submit → `POST /datasets/{id}/ask`. Disabled + spinner while running.
4. **Answer panel** (the payoff — all three, every time):
   - **Answer** — the numeric answer, prominent.
   - **Explanation** — the short plain-language paragraph.
   - **Code** — a monospace code block showing the exact pandas the agent ran, with a copy
     button. Labelled "The exact code that produced this answer" to reinforce auditability.
5. **Error state** — human-readable message, never a stack trace.
6. **Empty state** — "Upload a CSV to get started" before any upload.

### Labelled NON-FUNCTIONAL stubs (visible, inert, "Coming soon")
Each is rendered but disabled/greyed with a visible "Coming soon" tag so it is never mistaken
for a bug:
- **Add another file** (multi-file) — greyed control next to upload.
- **.xlsx upload** — a "coming soon" badge on the upload control (wired in Phase 3).
- **Charts** — a placeholder panel "Charts (coming soon)" below the answer (wired in Phase 4).
- **Continue the conversation** — a disabled follow-up question box (wired in Phase 2).
- **Connect a database** — a disabled "Connect a database (coming soon)" button.

## Interactions / states
| State | Trigger | UI |
|-------|---------|----|
| idle | initial | empty state, question box disabled |
| uploaded | upload success | filename + schema chips, question box enabled |
| analyzing | Analyze clicked | spinner, inputs disabled |
| answered | `/ask` success | answer + explanation + code panel |
| error | upload/ask failure | human-readable error banner |

## Phase wiring of stubs
- Phase 2 → "Continue the conversation" becomes a live thread.
- Phase 3 → `.xlsx` upload enabled, badge dropped.
- Phase 4 → "Charts" panel renders a real chart.
- Multi-file and DB connections remain labelled stubs (out of current roadmap scope).

> **Assumed:** Styling via Tailwind (already configured in the baseline). Client charting library
> (Phase 4) chosen by the frontend generator (lightweight, static-export compatible).
