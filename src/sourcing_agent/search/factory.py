from __future__ import annotations

from sourcing_agent.config.settings import get_settings
from sourcing_agent.search.base import SearchProvider
from sourcing_agent.search.stub import StubSearchProvider
from sourcing_agent.search.tavily import TavilySearchProvider


def create_search_provider() -> SearchProvider:
    s = get_settings()
    if s.resolved_search_provider == "tavily":
        return TavilySearchProvider(api_key=s.tavily_api_key)
    return StubSearchProvider()
