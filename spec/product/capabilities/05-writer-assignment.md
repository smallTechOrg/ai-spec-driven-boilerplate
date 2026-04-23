# Capability: Writer Assignment

## What It Does

Assigns a writer persona to each topic in a generation run, distributing topics evenly across all active writers.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|---------|
| topics | list[str] | Topic discovery output | yes |
| active_writers | list[Writer] | DB (is_active = true) | yes |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| assignments | list[tuple[str, Writer]] | GenerationState (topic → writer pairs) |

## External Calls

None. Pure Python logic.

## Business Rules

- Only writers with `is_active = true` are eligible
- Assignment is round-robin: topics[0] → writers[0], topics[1] → writers[1], ..., wraps around
- If there is only one active writer, all topics go to that writer
- Writer order is sorted by `id` (deterministic)
- If there are no active writers: raise a hard error before the run starts (blocked at API layer)

## Success Criteria

- [ ] Every topic has exactly one writer assigned
- [ ] With N writers and M topics, no writer is assigned more than `ceil(M/N)` topics
- [ ] Assignment is deterministic given the same input (same topic list, same writer list → same output)
- [ ] Raises ValueError if active_writers is empty
