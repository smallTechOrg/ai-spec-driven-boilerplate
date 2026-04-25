from __future__ import annotations


class TavilySearchProvider:
    name = "tavily"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client = None

    def _get_client(self):
        if self._client is None:
            from tavily import TavilyClient  # type: ignore

            self._client = TavilyClient(api_key=self._api_key)
        return self._client

    def search(self, query: str, max_results: int = 5) -> list[dict]:
        client = self._get_client()
        resp = client.search(query=query, max_results=max_results)
        out: list[dict] = []
        for r in resp.get("results", []):
            out.append(
                {
                    "name": r.get("title", "Unknown"),
                    "url": r.get("url"),
                    "snippet": r.get("content", ""),
                    "location": "",
                }
            )
        return out
