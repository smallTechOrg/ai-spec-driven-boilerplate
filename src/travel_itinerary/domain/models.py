from __future__ import annotations

import datetime

from pydantic import BaseModel


class Place(BaseModel):
    name: str
    description: str
    tips: str


class Dish(BaseModel):
    name: str
    description: str


class HotelInfo(BaseModel):
    estimated_price_range: str  # e.g. "$80–$150 per night"
    notes: str                  # e.g. "Prices higher in peak season"
    booking_url: str            # Booking.com deep-link (generated, not from LLM)


class ItineraryResponse(BaseModel):
    city: str
    places: list[Place]
    dish: Dish
    hotel: HotelInfo


# ── Hotel Booking ──────────────────────────────────────────────────────────────

class HotelSearchParams(BaseModel):
    city: str
    checkin: datetime.date
    checkout: datetime.date
    guests: int
    budget_min: int   # USD per night
    budget_max: int   # USD per night
    star_rating: int  # 1–5


class HotelRecommendation(BaseModel):
    name: str
    description: str
    amenities: list[str]
    estimated_price: str   # e.g. "$95–$120 per night"
    booking_url: str       # built by Python, never by LLM


class HotelSearchResult(BaseModel):
    city: str
    hotels: list[HotelRecommendation]

