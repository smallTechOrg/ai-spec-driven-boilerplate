from prmonitor.domain.models import PR

STUB_PRS = [
    PR(repo="acme/backend", number=42, title="Add OAuth2 login", author="alice", days_open=5, url="https://github.com/acme/backend/pull/42"),
    PR(repo="acme/frontend", number=17, title="Dark mode toggle", author="bob", days_open=4, url="https://github.com/acme/frontend/pull/17"),
    PR(repo="acme/infra", number=8, title="Upgrade Terraform to 1.7", author="carol", days_open=7, url="https://github.com/acme/infra/pull/8"),
]

async def fetch_stale_prs(org: str, token: str, stale_days: int) -> list[PR]:
    """Stub: returns hardcoded stale PRs."""
    return STUB_PRS
