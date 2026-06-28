# Capability: Multi-File Join & Folder-as-Dataset

> **DEFERRED — Phase 3.** In Phase 1 the multi-file join / dataset picker is a LABELLED stub. This file specifies the target behaviour.

## What It Does
Lets the user join/compare two datasets, treat a folder of like-shaped files as one combined dataset, and have the agent auto-pick the right file(s) for a question.

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|----------|
| dataset_ids | list of uuid | UI / auto-pick | yes |
| folder path | string | UI (folder-as-dataset) | yes (for folder ingest) |
| question | string | UI | yes |

## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| joined/combined answer | rich-answer envelope | `POST /api/ask` (multi-dataset) |
| folder dataset | combined library entry | `POST /api/datasets/folder` |
| datasets used | which dataset(s) the answer drew on | answer metadata |

## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| DuckDB (local) | cross-dataset JOIN / UNION of like-schema files | run `failed`, attempted SQL surfaced |
| Gemini (`gemini-2.5-flash`) | auto-pick dataset(s) from schemas only | retry → fatal |

## Business Rules
- Folder-as-dataset UNIONs files with compatible schemas; mismatched schemas are reported, not silently dropped.
- Auto-pick chooses dataset(s) from schemas only — no raw rows.
- Privacy boundary holds across all joined datasets.

## Success Criteria
- [ ] A join across two seeded datasets returns a correct aggregate (integration test).
- [ ] A folder of like CSVs is queryable as one dataset.
- [ ] The privacy-boundary test passes across multiple datasets in one ask.
