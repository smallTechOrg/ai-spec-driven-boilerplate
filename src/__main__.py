import uvicorn

from src.api.app import app  # noqa: F401 — imported so uvicorn can find it
from src.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "src.api.app:app",
        host=settings.analyst_host,
        port=settings.analyst_port,
        reload=False,
    )
