# Capability: Fetch Standups

## What It Does
Returns all standup updates for a given date.

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|---------|
| date | string YYYY-MM-DD | query param | yes |

## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| standups | Standup[] | JSON response |

## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| PostgreSQL | SELECT WHERE date | Return 500 |

## Success Criteria
- [ ] Returns all standups for the given date
- [ ] Empty array if no standups that day
