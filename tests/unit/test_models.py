from travel_itinerary.domain.models import Dish, HotelInfo, ItineraryResponse, Place


def test_place_model():
    p = Place(name="Eiffel Tower", description="Iconic iron tower.", tips="Open 9am-11pm. Book online.")
    assert p.name == "Eiffel Tower"
    assert p.description
    assert p.tips


def test_dish_model():
    d = Dish(name="Croissant", description="Buttery flaky pastry.")
    assert d.name == "Croissant"
    assert d.description


def test_hotel_info_model():
    h = HotelInfo(
        estimated_price_range="$80–$150 per night",
        notes="Book early in summer.",
        booking_url="https://www.booking.com/searchresults.html?ss=Paris&nflt=class%3D3",
    )
    assert h.estimated_price_range
    assert h.notes
    assert h.booking_url.startswith("https://")


def test_itinerary_response_model():
    places = [
        Place(name=f"Place {i}", description="Desc", tips="Tips") for i in range(3)
    ]
    dish = Dish(name="Baguette", description="French bread.")
    hotel = HotelInfo(
        estimated_price_range="$90–$140 per night",
        notes="Book ahead.",
        booking_url="https://www.booking.com/searchresults.html?ss=Paris&nflt=class%3D3",
    )
    resp = ItineraryResponse(city="Paris", places=places, dish=dish, hotel=hotel)
    assert resp.city == "Paris"
    assert len(resp.places) == 3
    assert resp.dish.name == "Baguette"
    assert resp.hotel.booking_url


def test_itinerary_response_serialization():
    places = [Place(name=f"P{i}", description="d", tips="t") for i in range(3)]
    dish = Dish(name="Dish", description="d")
    hotel = HotelInfo(
        estimated_price_range="$70–$120 per night",
        notes="Good rates off-season.",
        booking_url="https://www.booking.com/searchresults.html?ss=Rome&nflt=class%3D3",
    )
    resp = ItineraryResponse(city="Rome", places=places, dish=dish, hotel=hotel)
    data = resp.model_dump()
    assert data["city"] == "Rome"
    assert len(data["places"]) == 3
    assert "booking_url" in data["hotel"]
