"""Response envelope — every route returns ok(data) or raises api_error() (JSON)."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from fastapi.responses import JSONResponse


def ok(data: Any, status: int = 200) -> JSONResponse:
    return JSONResponse({"ok": True, "data": data}, status_code=status)


def api_error(code: str, message: str, status: int = 400) -> HTTPException:
    return HTTPException(
        status_code=status, detail={"ok": False, "error": {"code": code, "message": message}}
    )
