from __future__ import annotations

from typing import Protocol


class SearchProvider(Protocol):
    name: str

    def search(self, query: str, max_results: int = 5) -> list[dict]:
        ...
