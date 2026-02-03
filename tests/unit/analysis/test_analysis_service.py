"""
Unit tests for AnalysisService fit score and skills logic (Phase 2 Testing Strategy).
Uses canned transcript and mocked repositories.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
from uuid import uuid4

from src.screening.analysis.application.services import AnalysisService
from src.screening.analysis.application.services.analysis_service import (
    _compute_fit_score_and_skills,
)
from src.screening.calls.domain.entities import TranscriptSegment
from src.screening.shared.domain import ApplicationId, CallId, CandidateId, JobOfferId
from src.screening.applications.domain.entities import Candidate, JobOffer, ScreeningApplication


@pytest.fixture
def canned_transcript():
    return [
        TranscriptSegment("emma", "Hello, tell me about your experience.", 0.0),
        TranscriptSegment("candidate", "I have five years of Python and Java.", 1.0),
        TranscriptSegment("emma", "What interests you about this role?", 2.0),
        TranscriptSegment("candidate", "I like communication and teamwork.", 3.0),
    ]


@pytest.fixture
def candidate_with_skills():
    return Candidate(
        id=CandidateId(uuid4()),
        username="johndoe",
        full_name="John Doe",
        skills=["Python", "Java", "communication"],
        jobs=[],
    )


@pytest.fixture
def job_offer_with_strengths():
    return JobOffer(
        id=JobOfferId(uuid4()),
        external_id="job123",
        objective="Build APIs",
        strengths=["Python", "communication", "teamwork"],
        responsibilities=["Code review", "Mentoring"],
    )


@pytest.fixture
def mock_call_repository(canned_transcript):
    repo = MagicMock()
    call = MagicMock()
    call.transcript = canned_transcript
    repo.get_call = MagicMock(return_value=call)
    return repo


@pytest.fixture
def mock_application_repository(candidate_with_skills, job_offer_with_strengths):
    repo = MagicMock()
    app = ScreeningApplication(
        id=ApplicationId(uuid4()),
        candidate_id=candidate_with_skills.id,
        job_offer_id=job_offer_with_strengths.id,
        created_at=datetime.utcnow(),
    )
    repo.get_application = AsyncMock(return_value=app)
    repo.get_candidate = MagicMock(return_value=candidate_with_skills)
    repo.get_job_offer = MagicMock(return_value=job_offer_with_strengths)
    return repo


@pytest.fixture
def mock_analysis_repository():
    repo = MagicMock()
    return repo


@pytest.fixture
def analysis_service(mock_call_repository, mock_application_repository, mock_analysis_repository):
    return AnalysisService(
        get_call_repository=lambda: mock_call_repository,
        get_application_repository=lambda: mock_application_repository,
        get_embeddings=None,
        analysis_repository=mock_analysis_repository,
    )


@pytest.mark.asyncio
async def test_run_analysis_persists_fit_score_and_skills(
    analysis_service, mock_call_repository, mock_application_repository, mock_analysis_repository,
    canned_transcript, candidate_with_skills, job_offer_with_strengths
):
    app_id = ApplicationId(uuid4())
    call_id = CallId(uuid4())
    await analysis_service.run_analysis(app_id, call_id)
    mock_analysis_repository.upsert_by_application.assert_called_once()
    analysis = mock_analysis_repository.upsert_by_application.call_args[0][0]
    assert analysis.application_id == app_id
    assert 0 <= analysis.fit_score <= 100
    assert isinstance(analysis.skills, list)
    assert "Python" in analysis.skills or "communication" in analysis.skills


def test_compute_fit_score_empty_transcript_returns_zero_and_empty_skills():
    score, skills = _compute_fit_score_and_skills([], None, None, None)
    assert score == 0
    assert skills == []


def test_compute_fit_score_single_segment_returns_zero():
    score, skills = _compute_fit_score_and_skills(
        [TranscriptSegment("emma", "Hi", 0.0)], None, None, None
    )
    assert score == 0
    assert skills == []


def test_compute_fit_score_matches_job_strengths_in_transcript(
    canned_transcript, job_offer_with_strengths
):
    score, skills = _compute_fit_score_and_skills(
        canned_transcript, None, job_offer_with_strengths, None
    )
    assert score >= 40
    assert score <= 100
    assert "Python" in skills
    assert "communication" in skills


def test_compute_fit_score_fallback_to_candidate_skills_when_no_job_match(
    canned_transcript, candidate_with_skills
):
    job_no_match = JobOffer(
        id=JobOfferId(uuid4()),
        external_id="x",
        objective="X",
        strengths=["Rust", "Go"],
        responsibilities=[],
    )
    score, skills = _compute_fit_score_and_skills(
        canned_transcript, candidate_with_skills, job_no_match, None
    )
    assert score >= 40
    assert len(skills) <= 5
