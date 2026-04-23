import asyncio
import sys
from prmonitor.agent.runner import run_agent

def main() -> None:
    asyncio.run(run_agent())

if __name__ == "__main__":
    main()
