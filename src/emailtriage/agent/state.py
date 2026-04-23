from typing import TypedDict, Optional
from emailtriage.domain.models import Email, EmailResult

class TriageState(TypedDict):
    run_id: int
    emails: list[Email]
    results: list[EmailResult]
    error: Optional[str]
