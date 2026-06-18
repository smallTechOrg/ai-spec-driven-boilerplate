"""Run the DataChat API server (port 8001 unless PORT overrides)."""

from __future__ import annotations

import os

import uvicorn


def main() -> None:
    port = int(os.environ.get("PORT", "8001"))
    uvicorn.run("datachat.api:app", host="0.0.0.0", port=port, reload=False)


if __name__ == "__main__":
    main()
