import uvicorn

from food_tracker.api import create_app
from food_tracker.config.settings import get_settings

app = create_app()

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run("food_tracker.__main__:app", host="0.0.0.0", port=settings.port, reload=False)
