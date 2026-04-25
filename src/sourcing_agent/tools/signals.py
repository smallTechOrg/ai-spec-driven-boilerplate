"""Per-supplier signal gathering — runs a follow-up search asking for
reviews / ratings / GST / years-in-business so the enrich step has actual
review-bearing snippets to summarize."""
from __future__ import annotations

from sourcing_agent.search.factory import create_search_provider


def gather_signals(supplier_name: str, location: str, max_results: int = 4) -> list[dict]:
    """Return raw search snippets about a supplier's reputation."""
    if not supplier_name:
        return []
    provider = create_search_provider()
    query = (
        f'"{supplier_name}" {location} reviews rating GST years '
        "site:google.com OR site:justdial.com OR site:indiamart.com OR site:tradeindia.com"
    )
    return provider.search(query=query, max_results=max_results)


def attach_signals_to_results(
    raw_results: list[dict], location: str
) -> list[dict]:
    """For each search hit, attach a `signals` list of supplemental snippets.

    The supplier name is best-extracted from the search hit's name/title.
    The signals provider is the same as the primary search provider — when in
    stub mode, results are deterministic and demo-friendly.
    """
    enriched: list[dict] = []
    for r in raw_results:
        name = _supplier_name_from_hit(r)
        signals = gather_signals(name, location) if name else []
        enriched.append({**r, "signals": signals})
    return enriched


def _supplier_name_from_hit(hit: dict) -> str:
    name = (hit.get("name") or "").strip()
    if not name:
        return ""
    # Strip common directory suffixes
    for sep in [" - IndiaMART", " | Justdial", " - Justdial", " | IndiaMART", " - Google"]:
        if sep in name:
            name = name.split(sep, 1)[0]
    # If the title is clearly a directory listing, try the snippet
    if name.lower().startswith(("bricks at", "cement at", "best price")):
        snippet = (hit.get("snippet") or "").strip()
        # Pull the first capitalized phrase as a likely company name
        import re

        m = re.search(r"\b([A-Z][A-Za-z0-9 &\.\-]{2,40})\b", snippet)
        if m:
            return m.group(1).strip()
    return name
