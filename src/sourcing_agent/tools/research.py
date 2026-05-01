from __future__ import annotations

from sourcing_agent.search.factory import create_search_provider


def research_suppliers(material: str, location: str, max_results: int = 5) -> list[dict]:
    provider = create_search_provider()
    query = f"{material} suppliers in {location}"
    return provider.search(query=query, max_results=max_results)
