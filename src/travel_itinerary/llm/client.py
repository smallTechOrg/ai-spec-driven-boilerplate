from __future__ import annotations

import json
import re
import urllib.parse

from travel_itinerary.config.settings import get_settings
from travel_itinerary.domain.models import HotelSearchParams, HotelSearchResult, ItineraryResponse
from travel_itinerary.llm.providers import GeminiProvider, LLMProvider, StubProvider

ITINERARY_PROMPT = """\
You are a travel guide. Given a city, return a JSON object with exactly this structure:

{{
  "city": "<city name>",
  "places": [
    {{
      "name": "<place name>",
      "description": "<2-3 sentence description>",
      "tips": "<opening hours and one practical visitor tip>"
    }},
    ... (exactly 3 places)
  ],
  "dish": {{
    "name": "<local dish name>",
    "description": "<1-2 sentence description of the dish>"
  }},
  "hotel": {{
    "estimated_price_range": "<typical nightly rate for a 3-star hotel, e.g. '$80\u2013$150 per night'>",
    "notes": "<one sentence tip on when to book or seasonal pricing>"
  }}
}}

City: {city}

Return ONLY the JSON object. No markdown, no explanation, no code fences.
"""

HOTEL_SEARCH_PROMPT = """\
<hotel_search>
You are a hotel recommendation agent. Given the search parameters below, suggest 3 real or \
realistic {star_rating}-star hotels in {city} that fit the budget of ${budget_min}\u2013${budget_max} per night \
for {guests} guest(s), checking in {checkin} and checking out {checkout}.

Return a JSON object with exactly this structure:
{{
  "hotels": [
    {{
      "name": "<hotel name>",
      "description": "<2-3 sentence description of the hotel and its location>",
      "amenities": ["<amenity 1>", "<amenity 2>", "<amenity 3>"],
      "estimated_price": "<estimated nightly rate within the budget, e.g. '$95\u2013$120 per night'>"
    }},
    ... (exactly 3 hotels)
  ]
}}

Return ONLY the JSON object. No markdown, no explanation, no code fences.
</hotel_search>
"""


def _booking_url(city: str) -> str:
    """Build a Booking.com 3-star hotel search URL for the given city."""
    return (
        "https://www.booking.com/searchresults.html?"
        + urllib.parse.urlencode({"ss": city, "nflt": "class=3"})
    )


def _booking_url_full(params: HotelSearchParams) -> str:
    """Build a pre-filled Booking.com search URL from HotelSearchParams."""
    price_filter = f"price=USD-{params.budget_min}-{params.budget_max}-1"
    star_filter = f"class={params.star_rating}"
    return (
        "https://www.booking.com/searchresults.html?"
        + urllib.parse.urlencode(
            {
                "ss": params.city,
                "checkin": params.checkin.isoformat(),
                "checkout": params.checkout.isoformat(),
                "group_adults": params.guests,
                "nflt": f"{star_filter};{price_filter}",
            }
        )
    )


def _strip_fences(raw: str) -> str:
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
    return re.sub(r"\s*```$", "", raw.strip(), flags=re.MULTILINE)


class LLMClient:
    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    @property
    def is_stub(self) -> bool:
        return isinstance(self._provider, StubProvider)

    def get_itinerary(self, city: str) -> ItineraryResponse:
        prompt = ITINERARY_PROMPT.format(city=city)
        raw = _strip_fences(self._provider.call(prompt))
        data = json.loads(raw)
        data["city"] = city
        # Booking URL is always generated here — never trusted from LLM output
        data.setdefault("hotel", {})
        data["hotel"]["booking_url"] = _booking_url(city)
        return ItineraryResponse.model_validate(data)

    def search_hotels(self, params: HotelSearchParams) -> HotelSearchResult:
        prompt = HOTEL_SEARCH_PROMPT.format(
            city=params.city,
            checkin=params.checkin.isoformat(),
            checkout=params.checkout.isoformat(),
            guests=params.guests,
            budget_min=params.budget_min,
            budget_max=params.budget_max,
            star_rating=params.star_rating,
        )
        raw = _strip_fences(self._provider.call(prompt))
        data = json.loads(raw)
        booking_url = _booking_url_full(params)
        for hotel in data.get("hotels", []):
            # Every hotel card links to the same pre-filled Booking.com search —
            # individual property URLs can't be safely generated without a live API.
            hotel["booking_url"] = booking_url
        return HotelSearchResult(city=params.city, hotels=data["hotels"])


def create_client() -> LLMClient:
    settings = get_settings()
    if settings.google_api_key:
        provider: LLMProvider = GeminiProvider(
            api_key=settings.google_api_key,
            model=settings.travel_llm_model,
        )
    else:
        provider = StubProvider()
    return LLMClient(provider)
