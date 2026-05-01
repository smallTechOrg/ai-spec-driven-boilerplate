"""
Integration tests for the full POST /analyze pipeline using the stub provider.

These tests use a real PostgreSQL database (food_tracker_test) and the stub LLM
provider — no Gemini API key is required.
"""
import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from food_tracker.api import create_app
from food_tracker.db.models import FoodLog


# Minimal valid 1×1 JPEG for upload tests (does not need to be a real food photo
# since the stub provider ignores image content)
_TINY_JPEG = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
    b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
    b"\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\x1e"
    b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00"
    b"\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b"
    b"\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04"
    b"\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa"
    b"\x07\"q\x142\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br"
    b"\x82\t\n\x16\x17\x18\x19\x1a%&'()*456789:CDEFGHIJSTUVWXYZ"
    b"cdefghijstuvwxyz\x83\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95"
    b"\x96\x97\x98\x99\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3"
    b"\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca"
    b"\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7"
    b"\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa"
    b"\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xfb\xd4P\x00\x00\x00\x1f\xff\xd9"
)


@pytest.fixture(scope="module")
def client(db_engine):
    """Create a TestClient backed by the test database."""
    import os
    from food_tracker.config.settings import get_settings
    from food_tracker.db import session as db_session_module
    from sqlalchemy.orm import sessionmaker

    # Wire the app to use the test engine
    test_session_factory = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)

    app = create_app()

    # Override the DB session dependency to use the test engine
    from food_tracker.db.session import get_session

    def override_get_session():
        session = test_session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_session] = override_get_session

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_upload_form_renders(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Food Tracker" in response.text
    assert "Upload a food photo" in response.text


def test_analyze_returns_nutrition_result(client, db_engine):
    response = client.post(
        "/analyze",
        files={"photo": ("food.jpg", io.BytesIO(_TINY_JPEG), "image/jpeg")},
    )
    assert response.status_code == 200
    html = response.text
    # Stub banner must be visible
    assert "DEMO MODE" in html
    # Stub food name is present
    assert "STUB" in html or "Grilled Chicken" in html
    # Nutrition values rendered
    assert "kcal" in html
    assert "protein" in html


def test_analyze_creates_db_record(client, db_engine):
    initial_count_result = db_engine.connect().execute(
        select(FoodLog)
    ).fetchall()
    initial_count = len(initial_count_result)

    client.post(
        "/analyze",
        files={"photo": ("burger.jpg", io.BytesIO(_TINY_JPEG), "image/jpeg")},
    )

    with db_engine.connect() as conn:
        rows = conn.execute(select(FoodLog)).fetchall()
    assert len(rows) == initial_count + 1


def test_analyze_rejects_missing_file(client):
    response = client.post("/analyze")
    assert response.status_code in (400, 422)


def test_analyze_rejects_large_file(client):
    big_data = b"\xff\xd8" + b"\x00" * (11 * 1024 * 1024)
    response = client.post(
        "/analyze",
        files={"photo": ("big.jpg", io.BytesIO(big_data), "image/jpeg")},
    )
    assert response.status_code == 400
