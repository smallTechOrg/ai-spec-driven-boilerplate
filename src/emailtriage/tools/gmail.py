from emailtriage.domain.models import Email

STUB_EMAILS = [
    Email(id="msg1", subject="URGENT: Server down", sender="ops@company.com", snippet="Production is down..."),
    Email(id="msg2", subject="Team lunch Friday?", sender="alice@company.com", snippet="Hey, want to grab lunch?"),
    Email(id="msg3", subject="Q3 report draft", sender="bob@company.com", snippet="Please review when you get a chance"),
]

async def fetch_unread_emails(credentials_path: str, max_results: int = 50) -> list[Email]:
    """Stub: returns hardcoded emails."""
    return STUB_EMAILS
