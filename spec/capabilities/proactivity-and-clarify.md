# Capability: Proactivity, Clarification & Watched Folder

> **DEFERRED — Phase 4.** In Phase 1 follow-up chips are display-only and the watched-folder control is a LABELLED stub. This file specifies the target behaviour.

## What It Does
Makes the agent proactive and safe under ambiguity: clickable follow-up suggestions that re-ask, a clarification gate that asks first when a question is ambiguous (or gives a flagged best-guess), and a watched local folder that auto-ingests dropped files.

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|----------|
| follow-up click | the suggested question text | UI chip | yes (to re-ask) |
| clarification answer | string | UI | no |
| watched folder path | string | UI (`POST /api/watch`) | yes (to enable) |

## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| re-asked answer | rich-answer envelope | `POST /api/ask` |
| clarification prompt | a question + (optional) flagged best-guess | `POST /api/ask/clarify` |
| auto-ingested datasets | new library entries from dropped files | watcher → library |

## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| Gemini (`gemini-2.5-flash`) | ambiguity check (clarify node) | retry → proceed with best-guess + flag |
| filesystem (watcher) | detect + ingest dropped files | log + skip the bad file |

## Business Rules
- Ambiguous question → ask first; if the user proceeds anyway, give a best-guess WITH a visible uncertainty flag.
- Clicking a follow-up chip re-asks that exact question against the active dataset.
- The watcher ingests via the same privacy-safe ingest path; no raw rows leave the machine.

## Success Criteria
- [ ] An ambiguous question triggers a clarification (integration test).
- [ ] Clicking a follow-up chip re-asks and returns a fresh answer.
- [ ] A file dropped into the watched folder auto-appears in the library.
