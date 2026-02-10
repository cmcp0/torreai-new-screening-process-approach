from abc import ABC, abstractmethod
from typing import Optional

from src.screening.applications.domain.entities import (
    Candidate,
    JobOffer,
    ScreeningApplication,
)
from src.screening.shared.domain import ApplicationId, CandidateId, JobOfferId


class ApplicationRepository(ABC):
    @abstractmethod
    async def find_application_by_username_and_job_offer(
        self, username: str, job_offer_id: str
    ) -> Optional[ScreeningApplication]:
        pass

    @abstractmethod
    async def save_candidate(self, candidate: Candidate) -> CandidateId:
        pass

    @abstractmethod
    async def save_job_offer(self, job_offer: JobOffer) -> JobOfferId:
        pass

    @abstractmethod
    async def save_application(
        self, application: ScreeningApplication
    ) -> ApplicationId:
        pass

    @abstractmethod
    async def save_application_graph(
        self,
        candidate: Candidate,
        job_offer: JobOffer,
        application: ScreeningApplication,
    ) -> ApplicationId:
        pass

    @abstractmethod
    async def get_application(self, application_id: ApplicationId) -> Optional[ScreeningApplication]:
        pass

    @abstractmethod
    def get_candidate(self, candidate_id: CandidateId) -> Optional[Candidate]:
        pass

    @abstractmethod
    def get_job_offer(self, job_offer_id: JobOfferId) -> Optional[JobOffer]:
        pass
