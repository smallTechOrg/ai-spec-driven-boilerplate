"""Offline search provider — returns 5 canned suppliers tagged with the
material and location the user requested. Believable for demos."""
from __future__ import annotations

CANNED_SUPPLIERS = [
    "Acme {material} Pvt Ltd",
    "{location} {material} Traders",
    "Bharat Building Materials",
    "Reliable Suppliers Co.",
    "GreenStone {material} Industries",
]


class StubSearchProvider:
    name = "stub"

    def search(self, query: str, max_results: int = 5) -> list[dict]:
        material, location = _parse_query(query)
        results: list[dict] = []
        for i, tmpl in enumerate(CANNED_SUPPLIERS[:max_results]):
            name = tmpl.format(material=_titleize(material), location=_titleize(location))
            slug = name.lower().replace(" ", "-")
            results.append(
                {
                    "name": name,
                    "location": _titleize(location),
                    "url": f"https://example.com/suppliers/{slug}",
                    "snippet": (
                        f"{name} supplies {material} in {location} and nearby "
                        f"districts. Listed on local trade directories with "
                        "indicative pricing and contact details."
                    ),
                }
            )
        return results


def _parse_query(query: str) -> tuple[str, str]:
    # Query shape from research tool: "{material} suppliers in {location}"
    parts = query.split(" in ", 1)
    if len(parts) == 2:
        material = parts[0].replace("suppliers", "").strip()
        return material or "construction material", parts[1].strip()
    return query, "your region"


def _titleize(s: str) -> str:
    return " ".join(w.capitalize() for w in s.split())
