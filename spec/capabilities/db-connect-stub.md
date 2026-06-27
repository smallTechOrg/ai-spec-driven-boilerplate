# Capability: Database Connect Stub (Phase 2)

## What It Does
Renders a clearly-labelled "Connect Database (Phase 2)" button in the data source panel that, when clicked, shows a modal explaining PostgreSQL connection is coming in Phase 2 — so the user sees the vision without mistaking a missing feature for a bug.

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|----------|
| user click | UI event | "Connect Database (Phase 2)" button | yes |

## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| Modal overlay | React component in DOM | Browser — message: "PostgreSQL database connection is coming in Phase 2. Stay tuned!" |

## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| None | N/A | N/A |

## Business Rules
- Button is styled as secondary/outline — visually distinct from the primary "Upload File" action
- Button label must include "(Phase 2)" so users understand it is intentionally unavailable
- Clicking opens a modal overlay (not a page navigation or error)
- Modal includes a close button
- The button is never disabled or hidden — it must always be clickable and produce the modal
- No backend call is made when the button is clicked

## Success Criteria
- [ ] "Connect Database (Phase 2)" button is visible in the data source panel
- [ ] Clicking the button opens a modal with the message "PostgreSQL database connection is coming in Phase 2"
- [ ] The modal can be closed by clicking the close button
- [ ] The button is styled differently from the primary upload action (secondary/outline)
- [ ] The button label contains "(Phase 2)" making its stub status unambiguous
