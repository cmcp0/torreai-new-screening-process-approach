from src.screening.applications.application.ports import EmbeddingRepository


class InMemoryEmbeddingRepository(EmbeddingRepository):
    def __init__(self) -> None:
        self._store: dict[str, list[float]] = {}

    def get_candidate_embedding(self, candidate_id: str) -> list[float] | None:
        return self._store.get(f"candidate:{candidate_id}")

    def get_job_offer_embedding(self, job_offer_id: str) -> list[float] | None:
        return self._store.get(f"job_offer:{job_offer_id}")

    def save_candidate_embedding(self, candidate_id: str, embedding: list[float]) -> None:
        self._store[f"candidate:{candidate_id}"] = embedding

    def save_job_offer_embedding(self, job_offer_id: str, embedding: list[float]) -> None:
        self._store[f"job_offer:{job_offer_id}"] = embedding
