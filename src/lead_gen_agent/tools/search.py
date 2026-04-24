"""Search tool — pluggable. Stub-safe; DuckDuckGo HTML implementation for Phase 3."""
from __future__ import annotations

from typing import Protocol

import httpx
from bs4 import BeautifulSoup


class SearchTool(Protocol):
    def search(self, query: str, limit: int = 10) -> list[dict]:
        """Return list of {title, url, snippet}."""
        ...


class DuckDuckGoSearch:
    """Scrapes DuckDuckGo's HTML-only endpoint. No API key required."""

    URL = "https://html.duckduckgo.com/html/"

    def search(self, query: str, limit: int = 10) -> list[dict]:
        try:
            resp = httpx.post(
                self.URL,
                data={"q": query},
                timeout=10.0,
                headers={"User-Agent": "Mozilla/5.0 lead-gen-agent"},
            )
            resp.raise_for_status()
        except httpx.HTTPError:
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        results: list[dict] = []
        for a in soup.select("a.result__a")[:limit]:
            title = a.get_text(strip=True)
            url = a.get("href", "")
            snippet_el = a.find_parent("div", class_="result__body")
            snippet = ""
            if snippet_el:
                sn = snippet_el.select_one(".result__snippet")
                if sn:
                    snippet = sn.get_text(" ", strip=True)
            results.append({"title": title, "url": url, "snippet": snippet})
        return results


class StubSearch:
    """Deterministic stub — returns synthetic SMB hits shaped like real results."""

    def search(self, query: str, limit: int = 10) -> list[dict]:
        base = [
            {
                "title": "Müller Präzisionstechnik GmbH — Precision manufacturing",
                "url": "https://mueller-praezision.example.de",
                "snippet": "Family-owned precision engineering firm in Stuttgart serving automotive suppliers since 1978. 80 employees.",
            },
            {
                "title": "Nordlicht Logistik AG — Regional freight & warehousing",
                "url": "https://nordlicht-logistik.example.de",
                "snippet": "Hamburg-based logistics SMB operating 30 trucks across northern Germany. Family run.",
            },
            {
                "title": "Rheinblick Weinhandel — Wholesale wine trade",
                "url": "https://rheinblick.example.de",
                "snippet": "Koblenz wholesaler sourcing from Rhine vintners. 25 staff. Traditional retail + restaurant supply.",
            },
        ]
        return base[:limit]


def get_search_tool(stub: bool = False) -> SearchTool:
    return StubSearch() if stub else DuckDuckGoSearch()
