from typing import Optional

from src.screening.applications.domain.entities import (
    Candidate,
    JobOffer,
    ScreeningApplication,
)
from src.screening.applications.application.ports import ApplicationRepository
from src.screening.shared.domain import ApplicationId, CandidateId, JobOfferId


class InMemoryApplicationRepository(ApplicationRepository):
    def __init__(self) -> None:
        self._candidates = {}
        self._job_offers = {}
        self._applications = {}
        self._username_job_index = {}

    async def find_application_by_username_and_job_offer(
        self, username: str, job_offer_id: str
    ) -> Optional[ScreeningApplication]:
        key = (username.strip().lower(), job_offer_id.strip())
        app_id = self._username_job_index.get(key)
        if app_id is None:
            return None
        return self._applications.get(str(app_id))

    async def save_candidate(self, candidate: Candidate) -> CandidateId:
        self._candidates[str(candidate.id)] = candidate
        return candidate.id

    async def save_job_offer(self, job_offer: JobOffer) -> JobOfferId:
        self._job_offers[str(job_offer.id)] = job_offer
        return job_offer.id

    async def save_application(
        self, application: ScreeningApplication
    ) -> ApplicationId:
        self._applications[str(application.id)] = application
        candidate = self._candidates.get(str(application.candidate_id))
        if candidate:
            job_offer = self._job_offers.get(str(application.job_offer_id))
            if job_offer:
                key = (candidate.username.lower(), job_offer.external_id)
                self._username_job_index[key] = application.id
        return application.id

    async def get_application(self, application_id: ApplicationId) -> Optional[ScreeningApplication]:
        return self._applications.get(str(application_id))

    def get_candidate(self, candidate_id: CandidateId) -> Optional[Candidate]:
        return self._candidates.get(str(candidate_id))

    def get_job_offer(self, job_offer_id: JobOfferId) -> Optional[JobOffer]:
        return self._job_offers.get(str(job_offer_id))
