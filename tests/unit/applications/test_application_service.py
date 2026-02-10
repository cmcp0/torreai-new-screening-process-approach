"""
Unit tests for ApplicationService (Phase 2 Testing Strategy).
Torre adapters and event publisher are mocked.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from src.screening.applications.application.services import ApplicationService
from src.screening.applications.application.services.application_service import (
    TorreNotFoundError,
)
from src.screening.applications.domain.value_objects import (
    CandidateFromTorre,
    JobOfferFromTorre,
)
from src.screening.applications.domain.events import JobOfferApplied
from src.screening.applications.infrastructure.adapters.in_memory_application_repository import (
    InMemoryApplicationRepository,
)
from src.screening.shared.domain import ApplicationId, CandidateId, JobOfferId


@pytest.fixture
def mock_bios():
    bios = AsyncMock()
    bios.get_bio = AsyncMock(
        return_value=CandidateFromTorre(
            username="johndoe",
            full_name="John Doe",
            skills=["Python", "Java"],
            jobs=[{"title": "Developer", "organization": "Acme"}],
        )
    )
    return bios


@pytest.fixture
def mock_opportunities():
    opp = AsyncMock()
    opp.get_opportunity = AsyncMock(
        return_value=JobOfferFromTorre(
            external_id="job123",
            objective="Build APIs",
            strengths=["Python", "communication"],
            responsibilities=["Code review", "Mentoring"],
        )
    )
    return opp


@pytest.fixture
def mock_repository():
    repo = AsyncMock()
    repo.find_application_by_username_and_job_offer = AsyncMock(return_value=None)
    repo.save_candidate = AsyncMock(return_value=CandidateId("00000000-0000-0000-0000-000000000001"))
    repo.save_job_offer = AsyncMock(return_value=JobOfferId("00000000-0000-0000-0000-000000000002"))
    repo.save_application = AsyncMock(return_value=ApplicationId("00000000-0000-0000-0000-000000000003"))
    repo.save_application_graph = AsyncMock(
        return_value=ApplicationId("00000000-0000-0000-0000-000000000003")
    )
    return repo


@pytest.fixture
def mock_event_publisher():
    pub = MagicMock()
    pub.publish = MagicMock()
    return pub


@pytest.fixture
def application_service(mock_bios, mock_opportunities, mock_repository, mock_event_publisher):
    return ApplicationService(
        bios=mock_bios,
        opportunities=mock_opportunities,
        repository=mock_repository,
        event_publisher=mock_event_publisher,
    )


@pytest.mark.asyncio
async def test_create_application_returns_201_and_publishes_event(
    application_service, mock_bios, mock_opportunities, mock_repository, mock_event_publisher
):
    result = await application_service.create_application("johndoe", "job123")
    assert result.application_id is not None
    assert result.created is True
    mock_bios.get_bio.assert_awaited_once_with("johndoe")
    mock_opportunities.get_opportunity.assert_awaited_once_with("job123")
    mock_repository.save_application_graph.assert_awaited_once()
    mock_event_publisher.publish.assert_called_once()
    event = mock_event_publisher.publish.call_args[0][0]
    assert isinstance(event, JobOfferApplied)
    assert event.application_id == result.application_id


@pytest.mark.asyncio
async def test_create_application_raises_when_username_empty(application_service):
    with pytest.raises(ValueError, match="username and job_offer_id are required"):
        await application_service.create_application("", "job123")


@pytest.mark.asyncio
async def test_create_application_raises_when_job_offer_id_empty(application_service):
    with pytest.raises(ValueError, match="username and job_offer_id are required"):
        await application_service.create_application("johndoe", "")


@pytest.mark.asyncio
async def test_create_application_raises_torre_not_found_when_bio_missing(
    application_service, mock_bios
):
    mock_bios.get_bio = AsyncMock(return_value=None)
    with pytest.raises(TorreNotFoundError, match="Candidate not found"):
        await application_service.create_application("unknown", "job123")


@pytest.mark.asyncio
async def test_create_application_raises_torre_not_found_when_opportunity_missing(
    application_service, mock_opportunities
):
    mock_opportunities.get_opportunity = AsyncMock(return_value=None)
    with pytest.raises(TorreNotFoundError, match="Job offer not found"):
        await application_service.create_application("johndoe", "missing")


@pytest.mark.asyncio
async def test_create_application_idempotent_when_duplicate(
    application_service, mock_repository, mock_event_publisher
):
    from src.screening.applications.domain.entities import ScreeningApplication
    from datetime import datetime

    existing_id = ApplicationId("00000000-0000-0000-0000-000000000099")
    mock_repository.find_application_by_username_and_job_offer = AsyncMock(
        return_value=ScreeningApplication(
            id=existing_id,
            candidate_id=CandidateId("00000000-0000-0000-0000-000000000001"),
            job_offer_id=JobOfferId("00000000-0000-0000-0000-000000000002"),
            created_at=datetime.utcnow(),
        )
    )
    result = await application_service.create_application("johndoe", "job123")
    assert result.application_id == existing_id
    assert result.created is False
    mock_event_publisher.publish.assert_not_called()


@pytest.mark.asyncio
async def test_create_application_best_effort_idempotent_within_process():
    class SlowBios:
        async def get_bio(self, username: str):
            await asyncio.sleep(0.01)
            return CandidateFromTorre(
                username=username,
                full_name="John Doe",
                skills=["Python"],
                jobs=[],
            )

    class SlowOpportunities:
        async def get_opportunity(self, job_offer_id: str):
            await asyncio.sleep(0.01)
            return JobOfferFromTorre(
                external_id=job_offer_id,
                objective="Build APIs",
                strengths=["Python"],
                responsibilities=["Code review"],
            )

    repo = InMemoryApplicationRepository()
    event_publisher = MagicMock()
    event_publisher.publish = MagicMock()
    service = ApplicationService(
        bios=SlowBios(),
        opportunities=SlowOpportunities(),
        repository=repo,
        event_publisher=event_publisher,
    )

    first, second = await asyncio.gather(
        service.create_application("johndoe", "job123"),
        service.create_application("johndoe", "job123"),
    )

    assert str(first.application_id) == str(second.application_id)
    assert {first.created, second.created} == {True, False}
    event_publisher.publish.assert_called_once()
