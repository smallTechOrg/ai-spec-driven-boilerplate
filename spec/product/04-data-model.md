# Data Model

## EmailResult
| Field | Type | Notes |
|-------|------|-------|
| id | int PK | auto |
| email_id | str | Gmail message ID |
| subject | str | |
| sender | str | |
| classification | str | urgent / follow-up / ignore / error |
| draft_reply | str? | null unless urgent |
| processed_at | datetime | UTC |

## Run
| Field | Type | Notes |
|-------|------|-------|
| id | int PK | auto |
| ran_at | datetime | UTC |
| status | str | completed / failed |
| emails_processed | int | |
| error_message | str? | |
