from __future__ import annotations

import json
from abc import ABC, abstractmethod

from travel_itinerary.domain.models import Dish, HotelInfo, ItineraryResponse, Place

HOTEL_STUB_RESPONSE = {
    "hotels": [
        {
            "name": "Grand Plaza Hotel [STUB]",
            "description": "A well-located 3-star hotel with modern rooms and a rooftop bar, steps from the city centre.",
            "amenities": ["Free Wi-Fi", "Breakfast included", "Air conditioning", "24h front desk"],
            "estimated_price": "$85–$110 per night",
        },
        {
            "name": "City Inn Central [STUB]",
            "description": "Comfortable, clean rooms in a quiet street near public transport hubs.",
            "amenities": ["Free Wi-Fi", "Gym", "Non-smoking rooms", "Luggage storage"],
            "estimated_price": "$75–$95 per night",
        },
        {
            "name": "The Riverside Lodge [STUB]",
            "description": "Boutique 3-star hotel beside the river with scenic views and a popular restaurant.",
            "amenities": ["Free Wi-Fi", "River view", "Restaurant on-site", "Parking"],
            "estimated_price": "$95–$130 per night",
        },
    ]
}


class LLMProvider(ABC):
    @abstractmethod
    def call(self, prompt: str) -> str:
        """Send prompt to the LLM and return raw response string."""


class StubProvider(LLMProvider):
    """Offline stub that returns hardcoded data. Used when GOOGLE_API_KEY is absent."""

    def call(self, prompt: str) -> str:
        # Route to hotel stub when the prompt contains the hotel search marker
        if "<hotel_search>" in prompt:
            return json.dumps(HOTEL_STUB_RESPONSE)
        return json.dumps(
            {
                "city": "Demo City",
                "places": [
                    {
                        "name": "Grand Central Museum [STUB]",
                        "description": "A magnificent historic building housing one of the world's finest art collections.",
                        "tips": "Open 10am–6pm Tue–Sun. Free on the first Sunday of the month.",
                    },
                    {
                        "name": "Old Quarter [STUB]",
                        "description": "Cobblestone streets lined with centuries-old architecture and lively street markets.",
                        "tips": "Best explored on foot. Most shops open 9am–8pm daily.",
                    },
                    {
                        "name": "Riverside Promenade [STUB]",
                        "description": "A scenic waterfront walkway offering panoramic views of the city skyline.",
                        "tips": "Free to visit. Most beautiful at sunset. Cafés open until 11pm.",
                    },
                ],
                "dish": {
                    "name": "Local Stew [STUB]",
                    "description": "A hearty slow-cooked stew made with seasonal vegetables and local spices — a comfort food staple.",
                },
                "hotel": {
                    "estimated_price_range": "$80–$130 per night [STUB]",
                    "notes": "Prices vary by season. Book at least 2 weeks in advance for better rates.",
                },
            }
        )


class GeminiProvider(LLMProvider):
    """Real Google Gemini provider. Requires GOOGLE_API_KEY."""

    def __init__(self, api_key: str, model: str) -> None:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(model)

    def call(self, prompt: str) -> str:
        response = self._model.generate_content(prompt)
        return response.text

