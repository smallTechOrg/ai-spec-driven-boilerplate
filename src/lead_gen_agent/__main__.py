"""Entry point: uv run python -m lead_gen_agent"""
import uvicorn

from lead_gen_agent.api import create_app

app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "lead_gen_agent.__main__:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
    )
