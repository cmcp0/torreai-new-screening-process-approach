import logging
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

from src.screening.applications.domain.events import JobOfferApplied

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)
_BACKGROUND_SUBSCRIBERS = ThreadPoolExecutor(
    max_workers=3,
    thread_name_prefix="job_offer_applied",
)


def on_job_offer_applied(event: JobOfferApplied) -> None:
    # When this event is published from async request code (in-memory publisher),
    # run heavy subscribers in a worker thread so the event loop is not blocked.
    try:
        import asyncio

        asyncio.get_running_loop()
        _BACKGROUND_SUBSCRIBERS.submit(_run_subscribers, event)
        return
    except RuntimeError:
        pass
    except Exception as e:
        logger.warning("Falling back to sync JobOfferApplied subscribers: %s", e)

    # RabbitMQ consumer callbacks run in their own thread, so sync execution here
    # preserves delivery ordering and acknowledgment behavior.
    _run_subscribers(event)


def _run_subscribers(event: JobOfferApplied) -> None:
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
