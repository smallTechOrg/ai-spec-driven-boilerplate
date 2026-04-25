from __future__ import annotations

import uvicorn

from sourcing_agent.config.settings import get_settings


def main() -> None:
    s = get_settings()
    uvicorn.run(
        "sourcing_agent.api:app",
        host=s.host,
        port=s.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
