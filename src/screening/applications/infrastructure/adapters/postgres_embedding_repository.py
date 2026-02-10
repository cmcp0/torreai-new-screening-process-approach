from uuid import UUID, uuid4

from sqlalchemy import select

from src.screening.applications.application.ports import EmbeddingRepository
from src.screening.persistence.models import EntityEmbeddingModel


class PostgresEmbeddingRepository(EmbeddingRepository):
    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    def _get_embedding(self, entity_type: str, entity_id: str) -> list[float] | None:
        try:
            uid = UUID(entity_id)
        except (ValueError, TypeError):
            return None
        with self._session_factory() as session:
            row = (
                session.execute(
                    select(EntityEmbeddingModel).where(
                        EntityEmbeddingModel.entity_type == entity_type,
                        EntityEmbeddingModel.entity_id == uid,
                    )
                )
                .scalars()
                .first()
            )
            if row is None:
                return None
            emb = row.embedding if hasattr(row, "embedding") else None
            if isinstance(emb, list):
                return [float(x) for x in emb]
            return None

    def _save_embedding(self, entity_type: str, entity_id: str, embedding: list[float]) -> None:
        try:
            uid = UUID(entity_id)
        except (ValueError, TypeError):
            return
        with self._session_factory() as session:
            row = (
                session.execute(
                    select(EntityEmbeddingModel).where(
                        EntityEmbeddingModel.entity_type == entity_type,
                        EntityEmbeddingModel.entity_id == uid,
                    )
                )
                .scalars()
                .first()
            )
            if row is not None:
                row.embedding = embedding
            else:
                session.add(
                    EntityEmbeddingModel(
                        id=uuid4(),
                        entity_type=entity_type,
                        entity_id=uid,
                        embedding=embedding,
                    )
                )
            session.commit()

    def get_candidate_embedding(self, candidate_id: str) -> list[float] | None:
        return self._get_embedding("candidate", candidate_id)

    def get_job_offer_embedding(self, job_offer_id: str) -> list[float] | None:
        return self._get_embedding("job_offer", job_offer_id)

    def save_candidate_embedding(self, candidate_id: str, embedding: list[float]) -> None:
        self._save_embedding("candidate", candidate_id, embedding)

    def save_job_offer_embedding(self, job_offer_id: str, embedding: list[float]) -> None:
        self._save_embedding("job_offer", job_offer_id, embedding)
