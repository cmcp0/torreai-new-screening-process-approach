from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Callable, Optional, Protocol
from uuid import uuid4

from src.screening.analysis.domain.entities import ScreeningAnalysis
from src.screening.analysis.application.ports import AnalysisRepository
from src.screening.shared.domain import ApplicationId, AnalysisId, CallId
from src.shared.domain.events import DomainEvent

if TYPE_CHECKING:
    from src.screening.applications.application.ports import ApplicationRepository
    from src.screening.applications.domain.entities import Candidate, JobOffer
    from src.screening.calls.application.ports import CallRepository


@dataclass
class GetAnalysisResult:
    found_application: bool
    analysis: Optional[ScreeningAnalysis]


class EventPublisherPort(Protocol):
    def publish(self, event: DomainEvent) -> None:
        ...


class EmbeddingsLookupPort(Protocol):
    def __call__(
        self,
        candidate_id: str,
        job_offer_id: str,
    ) -> tuple[Optional[list[float]], Optional[list[float]]]:
        ...


class AnalysisService:
    """Fit-score: embedding similarity (0–100) when embeddings exist; else rule-based (transcript + skills). See docs/fit-score-algorithm.md."""

    def __init__(
        self,
        get_call_repository: Callable[[], Optional["CallRepository"]],
        get_application_repository: Callable[[], Optional["ApplicationRepository"]],
        get_embeddings: Optional[EmbeddingsLookupPort],
        analysis_repository: AnalysisRepository,
        event_publisher: Optional[EventPublisherPort] = None,
    ) -> None:
        self._get_call_repository = get_call_repository
        self._get_application_repository = get_application_repository
        self._get_embeddings = get_embeddings
        self._repository = analysis_repository
        self._event_publisher = event_publisher

    async def get_analysis_for_application(
        self, application_id: ApplicationId
    ) -> GetAnalysisResult:
        app_repo = self._get_application_repository()
        if app_repo is None:
            return GetAnalysisResult(found_application=False, analysis=None)
        app = await app_repo.get_application(application_id)
        if app is None:
            return GetAnalysisResult(found_application=False, analysis=None)
        analysis = await asyncio.to_thread(
            self._repository.get_by_application,
            application_id,
        )
        return GetAnalysisResult(found_application=True, analysis=analysis)

    async def run_analysis(self, application_id: ApplicationId, call_id: CallId) -> None:
        repo = self._get_call_repository()
        if repo is None:
            await asyncio.to_thread(_persist_default, self._repository, application_id)
            return
        call = await asyncio.to_thread(repo.get_call, call_id)
        if call is None:
            await asyncio.to_thread(_persist_default, self._repository, application_id)
            return
        transcript = call.transcript or []
        app_repo = self._get_application_repository()
        candidate = None
        job_offer = None
        if app_repo is not None:
            app = await app_repo.get_application(application_id)
            if app is not None:
                candidate = await asyncio.to_thread(
                    app_repo.get_candidate,
                    app.candidate_id,
                )
                job_offer = await asyncio.to_thread(
                    app_repo.get_job_offer,
                    app.job_offer_id,
                )

        fit_score, skills = await asyncio.to_thread(
            _compute_fit_score_and_skills,
            transcript,
            candidate,
            job_offer,
            self._get_embeddings,
        )
        analysis = ScreeningAnalysis(
            id=AnalysisId(uuid4()),
            application_id=application_id,
            fit_score=fit_score,
            skills=skills,
            completed_at=datetime.utcnow(),
            status="completed",
        )
        await asyncio.to_thread(self._repository.upsert_by_application, analysis)
        if self._event_publisher is not None:
            from src.screening.analysis.domain.events import AnalysisCompleted
            await asyncio.to_thread(
                self._event_publisher.publish,
                AnalysisCompleted(
                    application_id=application_id,
                    analysis_id=analysis.id,
                    occurred_at=datetime.utcnow(),
                ),
            )

    async def persist_analysis_failed(self, application_id: ApplicationId) -> None:
        """Persist a failed analysis so GET can return failed state."""
        analysis = ScreeningAnalysis(
            id=AnalysisId(uuid4()),
            application_id=application_id,
            fit_score=0,
            skills=[],
            completed_at=datetime.utcnow(),
            status="failed",
        )
        await asyncio.to_thread(self._repository.upsert_by_application, analysis)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _compute_fit_score_and_skills(
    transcript: list,
    candidate: Optional["Candidate"],
    job_offer: Optional["JobOffer"],
    get_embeddings: Optional[EmbeddingsLookupPort],
) -> tuple[int, list[str]]:
    """
    Fit-score: when embeddings available (get_embeddings set and both candidate and job
    embeddings exist), use cosine similarity mapped to 0-100. Otherwise fall back to
    rule-based: 40 + len(transcript)*5 + len(matched_skills)*10, capped at 100.
    Skills = job strengths mentioned in candidate transcript, or candidate skills.
    """
    skills: list[str] = []
    if transcript and len(transcript) >= 2:
        candidate_text = " ".join(
            s.text for s in transcript if getattr(s, "speaker", "") == "candidate"
        )
        if job_offer:
            for s in job_offer.strengths[:10]:
                if s and s.lower() in candidate_text.lower():
                    skills.append(s)
        if not skills and candidate:
            skills = list(candidate.skills[:5])
    skills = skills[:10]

    if get_embeddings and candidate and job_offer:
        cand_emb, job_emb = get_embeddings(str(candidate.id), str(job_offer.id))
        if cand_emb and job_emb and len(cand_emb) == len(job_emb):
            cos = _cosine_similarity(cand_emb, job_emb)
            score = int(round((cos + 1.0) / 2.0 * 100))
            return max(0, min(100, score)), skills

    if not transcript or len(transcript) < 2:
        return 0, skills
    candidate_text = " ".join(
        s.text for s in transcript if getattr(s, "speaker", "") == "candidate"
    )
    if not candidate_text.strip():
        return 0, skills
    score = min(100, 40 + len(transcript) * 5 + len(skills) * 10)
    return min(100, score), skills


def _persist_default(repository: AnalysisRepository, application_id: ApplicationId) -> None:
    analysis = ScreeningAnalysis(
        id=AnalysisId(uuid4()),
        application_id=application_id,
        fit_score=0,
        skills=[],
        completed_at=datetime.utcnow(),
        status="completed",
    )
    repository.upsert_by_application(analysis)
