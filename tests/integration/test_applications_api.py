"""
Integration tests: POST /api/applications (Phase 2 Testing Strategy).
Uses mocked Torre adapters (contract test).
"""
import pytest
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient

from apps.backend.main import app
from src.wiring import get_app_application_service
from src.screening.applications.application.services import ApplicationService
from src.screening.applications.domain.ports import TorreBiosPort, TorreOpportunitiesPort
from src.screening.applications.domain.value_objects import (
    CandidateFromTorre,
    JobOfferFromTorre,
)
from src.screening.applications.application.ports import ApplicationRepository
from src.screening.applications.domain.ports import EventPublisher
from src.screening.applications.infrastructure.adapters.in_memory_application_repository import (
    InMemoryApplicationRepository,
)
from src.screening.applications.infrastructure.adapters.in_memory_event_publisher import (
    InMemoryEventPublisher,
)
from src.screening.shared.domain import ApplicationId, CandidateId, JobOfferId


class MockBios(TorreBiosPort):
    async def get_bio(self, username: str):
        return CandidateFromTorre(
            username=username,
            full_name="Test User",
            skills=["Python"],
            jobs=[],
        )


class MockOpportunities(TorreOpportunitiesPort):
    async def get_opportunity(self, job_offer_id: str):
        return JobOfferFromTorre(
            external_id=job_offer_id,
            objective="Test role",
            strengths=["Python"],
            responsibilities=[],
        )


@pytest.fixture
def mock_event_publisher():
    return InMemoryEventPublisher()


@pytest.fixture
def test_application_service(mock_event_publisher):
    repo = InMemoryApplicationRepository()
    return ApplicationService(
        bios=MockBios(),
        opportunities=MockOpportunities(),
        repository=repo,
        event_publisher=mock_event_publisher,
    )


@pytest.fixture
def client(test_application_service):
    from apps.backend.routes.applications import get_application_service
    app.dependency_overrides[get_application_service] = lambda: test_application_service
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_application_service, None)


def test_post_applications_returns_201_and_application_id(client, mock_event_publisher):
    response = client.post(
        "/api/applications",
        json={"username": "testuser", "job_offer_id": "job123"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "application_id" in data
    assert len(data["application_id"]) > 0


def test_post_applications_duplicate_returns_201_idempotent(client):
    r1 = client.post("/api/applications", json={"username": "u", "job_offer_id": "j1"})
    assert r1.status_code == 201
    app_id = r1.json()["application_id"]
    r2 = client.post("/api/applications", json={"username": "u", "job_offer_id": "j1"})
    assert r2.status_code == 201
    assert r2.json()["application_id"] == app_id


def test_post_applications_missing_username_returns_400(client):
    response = client.post("/api/applications", json={"job_offer_id": "job123"})
    assert response.status_code == 422


def test_post_applications_empty_body_returns_422(client):
    response = client.post("/api/applications", json={})
    assert response.status_code == 422
