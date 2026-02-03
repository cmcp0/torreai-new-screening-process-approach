import logging
from typing import Any

from src.screening.applications.domain.events import JobOfferApplied

logger = logging.getLogger(__name__)

_embeddings_store: dict[str, list[float]] = {}


def get_candidate_embeddings(candidate_id: str) -> list[float] | None:
    return _embeddings_store.get(f"candidate:{candidate_id}")


def get_job_offer_embeddings(job_offer_id: str) -> list[float] | None:
    return _embeddings_store.get(f"job_offer:{job_offer_id}")


def _embed(text: str) -> list[float]:
    """Stub: return a deterministic fake embedding for POC. Replace with real adapter."""
    import hashlib
    h = int(hashlib.sha256(text.encode()).hexdigest()[:16], 16)
    return [((h >> i) % 1000) / 1000.0 for i in range(0, 64, 2)]


def generate_candidate_embeddings(event: JobOfferApplied) -> None:
    from src.screening.applications.application.ports import ApplicationRepository
    from src.wiring import get_application_repository

    repo: ApplicationRepository = get_application_repository()
    if not hasattr(repo, "get_candidate"):
        return
    candidate = repo.get_candidate(event.candidate_id)
    if candidate is None:
        return
    text_parts = [
        candidate.full_name,
        " ".join(candidate.skills),
        " ".join(str(j) for j in candidate.jobs[:5]),
    ]
    text = " ".join(text_parts)
    embedding = _embed(text)
    _embeddings_store[f"candidate:{event.candidate_id}"] = embedding


def generate_job_offer_embeddings(event: JobOfferApplied) -> None:
    from src.screening.applications.application.ports import ApplicationRepository
    from src.wiring import get_application_repository

    repo: ApplicationRepository = get_application_repository()
    if not hasattr(repo, "get_job_offer"):
        return
    job_offer = repo.get_job_offer(event.job_offer_id)
    if job_offer is None:
        return
    text_parts = [
        job_offer.objective,
        " ".join(job_offer.strengths),
        " ".join(job_offer.responsibilities),
    ]
    text = " ".join(text_parts)
    embedding = _embed(text)
    _embeddings_store[f"job_offer:{event.job_offer_id}"] = embedding
