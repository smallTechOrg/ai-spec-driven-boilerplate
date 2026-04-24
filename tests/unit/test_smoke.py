import travel_itinerary


def test_version():
    assert travel_itinerary.__version__ == "0.1.0"


def test_import_domain():
    from travel_itinerary.domain import Dish, ItineraryResponse, Place

    assert Place
    assert Dish
    assert ItineraryResponse


def test_import_config():
    from travel_itinerary.config import get_settings

    assert get_settings
