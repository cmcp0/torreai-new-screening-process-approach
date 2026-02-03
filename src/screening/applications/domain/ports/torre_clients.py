from abc import ABC, abstractmethod
from typing import Optional

from src.screening.applications.domain.value_objects import (
    CandidateFromTorre,
    JobOfferFromTorre,
)


class TorreBiosPort(ABC):
    @abstractmethod
    async def get_bio(self, username: str) -> Optional[CandidateFromTorre]:
        pass


class TorreOpportunitiesPort(ABC):
    @abstractmethod
    async def get_opportunity(self, job_offer_id: str) -> Optional[JobOfferFromTorre]:
        pass
