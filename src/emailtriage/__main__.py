import asyncio
from emailtriage.agent.runner import run_agent

def main():
    asyncio.run(run_agent())

if __name__ == "__main__":
    main()
