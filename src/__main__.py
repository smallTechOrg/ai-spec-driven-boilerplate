import sys
from pathlib import Path

import uvicorn

# `python -m src` puts the repo root on sys.path; bare imports (`api:app`,
# `config.settings`, ...) need the `src/` package dir itself on the path.
_SRC = str(Path(__file__).resolve().parent)
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8001, reload=False)
