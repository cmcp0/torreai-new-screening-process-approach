from abc import ABC, abstractmethod
from typing import List, Optional


class EmbeddingRepository(ABC):
    """Port for persisting and retrieving embeddings for candidates and job offers (FR-2.1, FR-2.2)."""

    @abstractmethod
    def get_candidate_embedding(self, candidate_id: str) -> Optional[List[float]]:
        pass

    @abstractmethod
    def get_job_offer_embedding(self, job_offer_id: str) -> Optional[List[float]]:
        pass

    @abstractmethod
    def save_candidate_embedding(self, candidate_id: str, embedding: List[float]) -> None:
        pass

    @abstractmethod
    def save_job_offer_embedding(self, job_offer_id: str, embedding: List[float]) -> None:
        pass
