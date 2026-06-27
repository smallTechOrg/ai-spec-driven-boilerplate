import sys
from pathlib import Path

# `python -m src` (run from repo root) does not put src/ on sys.path, so the
# bare `from api import app` import below would fail. Insert this file's own
# directory (the src/ dir) at the front of sys.path before importing.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import uvicorn

from api import app

if __name__ == "__main__":
    # Pass the app object directly (not an import string): reload would require
    # an import string and is intentionally disabled here.
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=False)
