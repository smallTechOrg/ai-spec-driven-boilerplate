import sys
from pathlib import Path

# Ensure src/ (this package's directory) is importable so `api:app` resolves the
# same way it does under pytest (pyproject `pythonpath = ["src"]`). This keeps the
# run path identical to the test path.
_SRC = str(Path(__file__).resolve().parent)
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import socket

import uvicorn

_HOST = "0.0.0.0"
_PORT = 8001


def _port_in_use(host: str, port: int) -> bool:
    """Cheap pre-flight: uvicorn logs a bind error but still exits 0, so check
    the port ourselves to fail loud (non-zero) when it is already taken."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return True
    return False


if __name__ == "__main__":
    if _port_in_use(_HOST, _PORT):
        print(
            f"ERROR: port {_PORT} is already in use — cannot start the server. "
            f"Stop the process using {_HOST}:{_PORT} and retry.",
            file=sys.stderr,
        )
        sys.exit(1)
    uvicorn.run("api:app", host=_HOST, port=_PORT, reload=False)
