from pathlib import Path
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
        app_dir=str(Path(__file__).parent),
    )
