"""Golden-path integration test: full registration → assessment → plan flow."""

import os
import uuid

import pytest
from starlette.testclient import TestClient

from up_police_ai.api import create_app
from up_police_ai.db.session import get_session


@pytest.fixture(scope="module")
def client():
    app = create_app()
    with TestClient(app, follow_redirects=True) as c:
        yield c


@pytest.fixture
def unique_badge():
    return f"TEST-{uuid.uuid4().hex[:8].upper()}"


# All 20 assessment scores (rating of 3 = intermediate level)
ASSESSMENT_DATA = {
    "a1": "3", "a2": "3", "a3": "3", "a4": "3", "a5": "3",
    "b1": "3", "b2": "3", "b3": "3", "b4": "3", "b5": "3",
    "c1": "3", "c2": "3", "c3": "3", "c4": "3", "c5": "3",
    "d1": "3", "d2": "3", "d3": "3", "d4": "3", "d5": "3",
}


def test_homepage_accessible(client):
    """Step 1: GET / returns 200 and contains expected text."""
    response = client.get("/")
    assert response.status_code == 200
    content = response.text
    assert "UP Police" in content or "Start" in content or "Register" in content


def test_health_check(client):
    """GET /health returns 200 with status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_full_golden_path(unique_badge):
    """Complete flow: register → assessment → plan → update status."""
    app = create_app()
    with TestClient(app, follow_redirects=True) as client:
        # Step 2: POST /register
        response = client.post(
            "/register",
            data={"name": "Test Officer Golden", "badge_number": unique_badge},
        )
        assert response.status_code == 200
        # After redirect, should be on assessment page
        assert "assessment" in response.url.path or "Section" in response.text or "question" in response.text.lower() or "Assessment" in response.text

        # Step 3: GET /assessment
        response = client.get("/assessment")
        assert response.status_code == 200
        assert "assessment" in response.url.path or "Section" in response.text or "Assessment" in response.text

        # Step 4: POST /assessment with all 20 scores
        response = client.post("/assessment", data=ASSESSMENT_DATA)
        assert response.status_code == 200
        # Should redirect to /plan
        assert "plan" in response.url.path

        # Step 5: GET /plan → contains officer name and "30"
        response = client.get("/plan")
        assert response.status_code == 200
        assert "Test Officer Golden" in response.text
        assert "30" in response.text

        # Step 6: Extract a day ID from the plan page to update status
        # Find a form action like /plan/day/{uuid}/status
        import re
        day_ids = re.findall(
            r'/plan/day/([0-9a-f-]{36})/status',
            response.text
        )
        assert len(day_ids) >= 1, "No day IDs found in plan page"
        first_day_id = day_ids[0]

        # POST status update to "done"
        response = client.post(
            f"/plan/day/{first_day_id}/status",
            data={"status": "done"},
        )
        assert response.status_code == 200
        assert "plan" in response.url.path

        # Step 7: Verify progress updated — page should now show at least 1 done
        response = client.get("/plan")
        assert response.status_code == 200
        # The done count should be at least 1/30
        assert "1/30" in response.text or "1/" in response.text


def test_register_existing_officer(unique_badge):
    """Registering with an existing badge number should login, not duplicate."""
    app = create_app()
    with TestClient(app, follow_redirects=True) as client:
        name = f"Officer {unique_badge}"

        # First registration
        client.post(
            "/register",
            data={"name": name, "badge_number": unique_badge},
        )
        # Submit assessment to get plan
        client.post("/assessment", data=ASSESSMENT_DATA)

        # Second registration with same badge — should go to plan
        response = client.post(
            "/register",
            data={"name": name, "badge_number": unique_badge},
        )
        assert response.status_code == 200
        assert "plan" in response.url.path


def test_logout_clears_session():
    """Logout should clear session and redirect to home."""
    app = create_app()
    badge = f"LOGOUT-{uuid.uuid4().hex[:8].upper()}"
    with TestClient(app, follow_redirects=True) as client:
        client.post(
            "/register",
            data={"name": "Logout Test Officer", "badge_number": badge},
        )
        response = client.get("/logout")
        assert response.status_code == 200
        # After logout and redirect to /, should NOT redirect to plan
        assert "plan" not in response.url.path


def test_assessment_requires_session():
    """GET /assessment without session should redirect to /."""
    app = create_app()
    with TestClient(app, follow_redirects=False) as client:
        response = client.get("/assessment")
        assert response.status_code == 302
        assert response.headers["location"] == "/"


def test_plan_requires_session():
    """GET /plan without session should redirect to /."""
    app = create_app()
    with TestClient(app, follow_redirects=False) as client:
        response = client.get("/plan")
        assert response.status_code == 302
        assert response.headers["location"] == "/"
