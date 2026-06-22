# Capability: Upload Dataset

## What It Does
Accepts a CSV upload and registers it as a queryable dataset.

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|----------|
| file | CSV file | multipart upload | yes |

## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| dataset record | {id, name, row_count, schema} | API response + datasets list |
| analytical table | columnar table `ds_<id>` | DuckDB |
| ingest audit entry | AuditLog row | metadata DB |

## External Calls
| System | Operation | On Failure |
|--------|-----------|-----------|
| DuckDB | create table from parsed CSV | return BAD_REQUEST, no Dataset row written |

## Business Rules
- Column schema (name + type) is captured and stored; row data lives only in DuckDB.
- An empty or unparseable file is rejected with BAD_REQUEST.
- Each successful ingest writes one AuditLog(operation=ingest).

## Success Criteria
- [ ] Uploading a valid CSV returns id, name, row_count, and a schema of {name,type} entries.
- [ ] The dataset's rows are queryable in DuckDB as `ds_<id>`.
- [ ] An ingest AuditLog row is written with status=success and the row count.
- [ ] An empty/garbage file returns BAD_REQUEST and writes no Dataset row.
