"""Entry point — run the sourcing agent web server."""

import uvicorn

from sourcing_agent.api import create_app

app = create_app()

if __name__ == "__main__":
    uvicorn.run("sourcing_agent.__main__:app", host="0.0.0.0", port=8001, reload=False)
