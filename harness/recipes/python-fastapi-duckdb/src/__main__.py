import uvicorn

from src.config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "src.api.app:app",
        host=settings.host,  # 127.0.0.1 by default; set APPNAME_HOST=0.0.0.0 in a container
        port=settings.port,
        reload=settings.env == "development",
    )
