import logging
from prmonitor.domain.models import PR
logger = logging.getLogger(__name__)

async def post_digest(webhook_url: str, prs: list[PR]) -> None:
    if not prs: return
    msg = "\n".join(f"• [{p.repo}] #{p.number} {p.title} ({p.author}, {p.days_open}d)" for p in prs)
    logger.info(f"[stub] would post to Slack:\n{msg}")
