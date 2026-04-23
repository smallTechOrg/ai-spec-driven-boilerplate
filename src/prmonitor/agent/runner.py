from prmonitor.config import settings
from prmonitor.db.repository import create_run, update_run
from prmonitor.db.session import get_session, init_db
from prmonitor.tools.github import fetch_stale_prs
from prmonitor.tools.slack import post_digest

async def run_agent() -> int:
    await init_db()
    async with get_session() as session:
        run = await create_run(session)
    try:
        prs = await fetch_stale_prs(settings.github_org, settings.github_token, settings.stale_days)
        await post_digest(settings.slack_webhook_url, prs)
        async with get_session() as session:
            await update_run(session, run.id, status="completed", stale_pr_count=len(prs))
        return run.id
    except Exception as exc:
        async with get_session() as session:
            await update_run(session, run.id, status="failed", error_message=str(exc))
        raise
