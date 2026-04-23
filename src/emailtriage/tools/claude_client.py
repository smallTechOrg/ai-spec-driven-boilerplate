from emailtriage.domain.models import Email

STUB_CLASSIFICATIONS = {
    "msg1": ("urgent", "Hi team, we are investigating the issue and will have an update in 15 minutes."),
    "msg2": ("ignore", None),
    "msg3": ("follow-up", None),
}

async def classify_email(email: Email, api_key: str) -> tuple[str, str | None]:
    """Stub: returns hardcoded classification and draft."""
    classification, draft = STUB_CLASSIFICATIONS.get(email.id, ("ignore", None))
    return classification, draft
