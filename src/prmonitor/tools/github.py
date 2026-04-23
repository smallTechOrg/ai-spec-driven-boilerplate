from prmonitor.domain.models import PR

STUB = [
    PR(repo="acme/api", number=12, title="Add rate limiting", author="alice", days_open=5, url="https://github.com/acme/api/pull/12"),
    PR(repo="acme/web", number=34, title="Fix login redirect", author="bob", days_open=4, url="https://github.com/acme/web/pull/34"),
]

async def fetch_stale_prs(org: str, token: str, stale_days: int) -> list[PR]:
    return STUB
