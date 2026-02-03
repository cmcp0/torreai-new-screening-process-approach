from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Callable, Optional
from uuid import uuid4

from src.screening.analysis.domain.entities import ScreeningAnalysis
from src.screening.shared.domain import ApplicationId, AnalysisId, CallId

if TYPE_CHECKING:
    from src.screening.analysis.application.ports import AnalysisRepository
    from src.screening.applications.domain.entities import Candidate, JobOffer


@dataclass
class GetAnalysisResult:
    found_application: bool
    analysis: Optional[ScreeningAnalysis]


class AnalysisService:
    """POC: fit-score is rule-based (transcript + skills match). get_embeddings=None; optional for future embedding similarity."""

    def __init__(
        self,
        get_call_repository: Callable[[], Optional[object]],
        get_application_repository: Callable[[], Optional[object]],
        get_embeddings: Optional[Callable[..., object]],
        analysis_repository: AnalysisRepository,
    ) -> None:
        self._get_call_repository = get_call_repository
        self._get_application_repository = get_application_repository
        self._get_embeddings = get_embeddings  # Optional in POC; used when embedding-based score is added
        self._repository = analysis_repository

    async def get_analysis_for_application(
        self, application_id: ApplicationId
    ) -> GetAnalysisResult:
        app_repo = self._get_application_repository()
        if not app_repo or not hasattr(app_repo, "get_application"):
            return GetAnalysisResult(found_application=False, analysis=None)
        app = await app_repo.get_application(application_id)
        if app is None:
            return GetAnalysisResult(found_application=False, analysis=None)
        analysis = self._repository.get_by_application(application_id)
        return GetAnalysisResult(found_application=True, analysis=analysis)

    async def run_analysis(self, application_id: ApplicationId, call_id: CallId) -> None:
        repo = self._get_call_repository()
        if repo is None:
            _persist_default(self._repository, application_id)
            return
        call = repo.get_call(call_id)
        if call is None:
            _persist_default(self._repository, application_id)
            return
        transcript = getattr(call, "transcript", []) or []
        app_repo = self._get_application_repository()
        candidate = None
        job_offer = None
        if app_repo is not None:
            app = await app_repo.get_application(application_id)
            if app is not None:
                candidate = app_repo.get_candidate(app.candidate_id)
                job_offer = app_repo.get_job_offer(app.job_offer_id)

        fit_score, skills = _compute_fit_score_and_skills(
            transcript=transcript,
            candidate=candidate,
            job_offer=job_offer,
            get_embeddings=self._get_embeddings,
        )
        analysis = ScreeningAnalysis(
            id=AnalysisId(uuid4()),
            application_id=application_id,
            fit_score=fit_score,
            skills=skills,
            completed_at=datetime.utcnow(),
        )
        self._repository.upsert_by_application(analysis)


def _compute_fit_score_and_skills(
    transcript: list,
    candidate: Optional["Candidate"],
    job_offer: Optional["JobOffer"],
    get_embeddings: Optional[Callable[..., object]],
) -> tuple[int, list[str]]:
    """
    POC fit-score algorithm (design spec: rule-based / embedding / LLM options).

    Chosen approach: rule-based. Score = 40 + len(transcript)*5 + len(matched_skills)*10,
    capped at 100. Skills = job strengths mentioned in candidate transcript, or candidate
    skills if no job match.

    Fallback when embeddings missing: not used in this implementation; embeddings adapter
    is optional. If added, score could use embedding similarity (candidate vs job) mapped
    to 0-100; when embeddings unavailable, fall back to this rule-based score.
    """
    if not transcript or len(transcript) < 2:
        return 0, []
    candidate_text = " ".join(
        getattr(s, "text", str(s)) for s in transcript if getattr(s, "speaker", "") == "candidate"
    )
    if not candidate_text.strip():
        return 0, []
    skills: list[str] = []
    if job_offer and hasattr(job_offer, "strengths"):
        for s in job_offer.strengths[:10]:
            if s and s.lower() in candidate_text.lower():
                skills.append(s)
    if not skills and candidate and hasattr(candidate, "skills"):
        skills = list(candidate.skills[:5])
    score = min(100, 40 + len(transcript) * 5 + len(skills) * 10)
    return min(100, score), skills[:10]


def _persist_default(repository: object, application_id: ApplicationId) -> None:
    from datetime import datetime
    from uuid import uuid4
    from src.screening.analysis.domain.entities import ScreeningAnalysis
    from src.screening.shared.domain import AnalysisId

    analysis = ScreeningAnalysis(
        id=AnalysisId(uuid4()),
        application_id=application_id,
        fit_score=0,
        skills=[],
        completed_at=datetime.utcnow(),
    )
    if hasattr(repository, "upsert_by_application"):
        repository.upsert_by_application(analysis)
