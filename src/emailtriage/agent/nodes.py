import logging
from datetime import datetime, timezone
from emailtriage.agent.state import TriageState
from emailtriage.config import settings
from emailtriage.db.repository import save_result, update_run
from emailtriage.db.session import get_session
from emailtriage.domain.models import EmailResult
from emailtriage.tools.gmail import fetch_unread_emails
from emailtriage.tools.claude_client import classify_email

logger = logging.getLogger(__name__)

async def fetch_emails(state: TriageState) -> dict:
    try:
        emails = await fetch_unread_emails("", settings.max_emails)
        return {"emails": emails, "error": None}
    except Exception as exc:
        return {"error": str(exc)}

async def classify_and_draft(state: TriageState) -> dict:
    results = []
    for email in state["emails"]:
        try:
            classification, draft = await classify_email(email, settings.anthropic_api_key)
            results.append(EmailResult(
                email_id=email.id, subject=email.subject, sender=email.sender,
                classification=classification, draft_reply=draft,
                processed_at=datetime.now(timezone.utc),
            ))
        except Exception as exc:
            logger.error("classify.failed", extra={"email_id": email.id, "error": str(exc)})
            results.append(EmailResult(
                email_id=email.id, subject=email.subject, sender=email.sender,
                classification="error", processed_at=datetime.now(timezone.utc),
            ))
    return {"results": results}

async def persist_results(state: TriageState) -> dict:
    for result in state["results"]:
        try:
            async with get_session() as session:
                await save_result(session, result)
        except Exception as exc:
            logger.error("persist.failed", extra={"email_id": result.email_id, "error": str(exc)})
    return {}

async def handle_error(state: TriageState) -> dict:
    async with get_session() as session:
        await update_run(session, state["run_id"], status="failed", error_message=state["error"])
    return {}

async def finalize(state: TriageState) -> dict:
    async with get_session() as session:
        await update_run(session, state["run_id"], status="completed",
                         emails_processed=len(state["results"]))
    return {}
