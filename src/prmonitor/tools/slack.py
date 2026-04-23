import logging
from prmonitor.domain.models import PR

logger = logging.getLogger(__name__)

async def post_digest(webhook_url: str, stale_prs: list[PR]) -> None:
    """Stub: logs to stdout instead of calling Slack."""
    if not stale_prs:
        return
    lines = ["*Stale PRs (open > 3 days):*"]
    for pr in stale_prs:
        lines.append(f"• [{pr.repo}] #{pr.number} — {pr.title} ({pr.author}, {pr.days_open}d)")
    logger.info("slack.stub.would_post:\n" + "\n".join(lines))
