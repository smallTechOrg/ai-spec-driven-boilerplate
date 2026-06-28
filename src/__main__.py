import sys
from pathlib import Path

# Ensure src/ is importable so the bare-package imports (`api`, `db`, ...) resolve
# whether launched via `python -m src` or `uvicorn`.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import uvicorn

from api import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=False)
