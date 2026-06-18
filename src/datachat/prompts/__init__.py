"""Load prompt templates from .md files at runtime."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_DIR = Path(__file__).parent


@lru_cache(maxsize=8)
def load(name: str) -> str:
    return (_DIR / f"{name}.md").read_text(encoding="utf-8")
