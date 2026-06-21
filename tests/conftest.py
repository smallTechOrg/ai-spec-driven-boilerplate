import pytest
from fastapi.testclient import TestClient

from src.api.app import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
