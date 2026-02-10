import hashlib
import logging
import time
from typing import List, Optional

import httpx

from src.screening.applications.domain.events import JobOfferApplied
from src.wiring import get_settings

logger = logging.getLogger(__name__)

_embeddings_store: dict[str, list[float]] = {}
_MAX_TEXT_LENGTH = 8000
_EMBED_RETRIES = 3
_EMBED_BACKOFF_BASE = 1.0


def get_candidate_embeddings(candidate_id: str) -> list[float] | None:
    return _embeddings_store.get(f"candidate:{candidate_id}")


def get_job_offer_embeddings(job_offer_id: str) -> list[float] | None:
    return _embeddings_store.get(f"job_offer:{job_offer_id}")


def _embed_stub(text: str) -> list[float]:
    """Deterministic fake embedding when Ollama is unavailable."""
    h = int(hashlib.sha256(text.encode()).hexdigest()[:16], 16)
    return [((h >> i) % 1000) / 1000.0 for i in range(0, 64, 2)]


def _embed_one_attempt(text: str) -> Optional[List[float]]:
    """Single attempt at Ollama /api/embed. Returns embedding list or None on failure."""
    settings = get_settings()
    base = (settings.ollama_base_url or "").strip().rstrip("/")
    if not base:
        return None
    url = f"{base}/api/embed"
    payload_text = (text or "").strip()[: _MAX_TEXT_LENGTH]
    if not payload_text:
        return None
    with httpx.Client(timeout=settings.ollama_timeout) as client:
        r = client.post(
            url,
            json={"model": settings.ollama_embed_model, "input": payload_text},
        )
        r.raise_for_status()
        data = r.json()
    emb_list = data.get("embeddings") or []
    embeddings = emb_list[0] if emb_list else []
    if isinstance(embeddings, list) and len(embeddings) > 0:
        return [float(x) for x in embeddings]
    return None


def _embed_with_retry(text: str) -> Optional[List[float]]:
    """Retry embedding 2-3 times with exponential backoff. Returns None on final failure."""
    for attempt in range(_EMBED_RETRIES):
        try:
            result = _embed_one_attempt(text)
            if result is not None:
                return result
        except Exception as e:
            logger.warning("Embed attempt %s failed: %s", attempt + 1, e)
        if attempt < _EMBED_RETRIES - 1:
            time.sleep(_EMBED_BACKOFF_BASE * (2 ** attempt))
    return None


def _embed(text: str) -> list[float]:
    """Generate embedding via Ollama /api/embed when configured; otherwise stub."""
    if not text or not text.strip():
        return _embed_stub("empty")
    result = _embed_with_retry(text)
    if result is not None:
        return result
    logger.warning("Ollama embeddings failed after %s attempts, using stub", _EMBED_RETRIES)
    return _embed_stub(text)


def _dead_letter_log(kind: str, event: JobOfferApplied, reason: str) -> None:
    """Log failed event for manual replay (dead-letter)."""
    payload = {
        "event": "JobOfferApplied",
        "application_id": str(event.application_id),
        "candidate_id": str(event.candidate_id),
        "job_offer_id": str(event.job_offer_id),
        "occurred_at": event.occurred_at.isoformat(),
    }
    logger.warning(
        "Embeddings dead-letter %s: %s – payload=%s",
        kind,
        reason,
        payload,
    )


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
    embedding = _embed_with_retry(text)
    if embedding is None:
        _dead_letter_log("candidate", event, "embed failed after retries")
        return
    _embeddings_store[f"candidate:{event.candidate_id}"] = embedding
    try:
        from src.wiring import get_embedding_repository
        repo = get_embedding_repository()
        repo.save_candidate_embedding(str(event.candidate_id), embedding)
    except Exception as e:
        logger.warning("Failed to persist candidate embedding: %s", e)


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
    embedding = _embed_with_retry(text)
    if embedding is None:
        _dead_letter_log("job_offer", event, "embed failed after retries")
        return
    _embeddings_store[f"job_offer:{event.job_offer_id}"] = embedding
    try:
        from src.wiring import get_embedding_repository
        repo = get_embedding_repository()
        repo.save_job_offer_embedding(str(event.job_offer_id), embedding)
    except Exception as e:
        logger.warning("Failed to persist job offer embedding: %s", e)
