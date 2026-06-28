import sys
from pathlib import Path

import uvicorn

# Modules use bare imports (`from api import ...`) — pytest puts `src/` on the
# path via [tool.pytest] pythonpath, but `python -m src` does not. Add this
# package's own directory so the import string `api:app` resolves at runtime.
_SRC_DIR = str(Path(__file__).resolve().parent)
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8001, reload=False)
