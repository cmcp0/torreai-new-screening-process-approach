"""
Integration tests: CORS middleware allows frontend origin (Phase 3).
"""
import pytest
from fastapi.testclient import TestClient

from apps.backend.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_cors_allows_frontend_origin(client):
    response = client.get(
        "/api/applications",
        headers={"Origin": "http://localhost:5173"},
    )
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_preflight_options(client):
    response = client.options(
        "/api/applications",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
