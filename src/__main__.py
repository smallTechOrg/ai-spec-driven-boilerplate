import os
import sys
from pathlib import Path

import uvicorn

# Make `src/` importable as the top-level package root so bare imports
# (`api`, `db`, `graph`, ...) resolve when launched via `uv run python -m src`.
_SRC_DIR = str(Path(__file__).resolve().parent)
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8001"))
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=False)
