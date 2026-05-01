import os
import uvicorn

from blogforge.api import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8001"))
    uvicorn.run(app, host="127.0.0.1", port=port)
