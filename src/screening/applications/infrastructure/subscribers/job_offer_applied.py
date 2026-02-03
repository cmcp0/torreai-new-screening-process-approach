import logging
from typing import TYPE_CHECKING

from src.screening.applications.domain.events import JobOfferApplied

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def on_job_offer_applied(event: JobOfferApplied) -> None:
    _generate_candidate_embeddings(event)
    _generate_job_offer_embeddings(event)
    _generate_call_prompt(event)


def _generate_candidate_embeddings(event: JobOfferApplied) -> None:
    try:
        from src.screening.applications.infrastructure.subscribers.embeddings import (
            generate_candidate_embeddings,
        )
        generate_candidate_embeddings(event)
    except Exception as e:
        logger.exception("GenerateCandidateEmbeddings failed: %s", e)


def _generate_job_offer_embeddings(event: JobOfferApplied) -> None:
    try:
        from src.screening.applications.infrastructure.subscribers.embeddings import (
            generate_job_offer_embeddings,
        )
        generate_job_offer_embeddings(event)
    except Exception as e:
        logger.exception("GenerateJobOfferEmbeddings failed: %s", e)


def _generate_call_prompt(event: JobOfferApplied) -> None:
    try:
        from src.screening.applications.infrastructure.subscribers.call_prompt import (
            generate_call_prompt,
        )
        generate_call_prompt(event)
    except Exception as e:
        logger.exception("GenerateCallPrompt failed: %s", e)
