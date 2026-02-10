import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Optional

from src.screening.applications.domain.events import JobOfferApplied

logger = logging.getLogger(__name__)

_call_prompts = {}
_PROMPT_RETRIES = 3
_PROMPT_BACKOFF_BASE = 0.5
_ASYNC_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="call_prompt_async")


def _run_async(coro):
    """Run an async coroutine from sync context in a dedicated thread with its own event loop."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@dataclass
class CallPromptData:
    prepared_questions: list
    role_context: str


_DEFAULT_PROMPT = CallPromptData(
    prepared_questions=["Tell me about your background."],
    role_context="Screening call.",
)


def get_call_prompt(application_id: str) -> Optional[CallPromptData]:
    return _call_prompts.get(application_id)


def _minimal_prompt_for_application(application_id: str) -> None:
    """Ensure a minimal prompt is stored so the call can start."""
    _call_prompts[application_id] = CallPromptData(
        prepared_questions=_DEFAULT_PROMPT.prepared_questions,
        role_context=_DEFAULT_PROMPT.role_context,
    )


def _generate_call_prompt_once(event: JobOfferApplied) -> None:
    from src.screening.applications.application.ports import ApplicationRepository
    from src.wiring import get_application_repository

    repo: ApplicationRepository = get_application_repository()
    future = _ASYNC_EXECUTOR.submit(
        _run_async, repo.get_application(event.application_id)
    )
    try:
        app = future.result(timeout=15.0)
    except Exception as e:
        logger.warning("Failed to load application for call prompt: %s", e)
        _minimal_prompt_for_application(str(event.application_id))
        return
    if app is None:
        return
    if not hasattr(repo, "get_job_offer") or not hasattr(repo, "get_candidate"):
        _minimal_prompt_for_application(str(event.application_id))
        return
    job_offer = repo.get_job_offer(event.job_offer_id)
    candidate = repo.get_candidate(event.candidate_id)
    if job_offer is None:
        _minimal_prompt_for_application(str(event.application_id))
        return
    role_context = (
        f"Objective: {job_offer.objective}\n"
        f"Strengths: {', '.join(job_offer.strengths[:5])}\n"
        f"Responsibilities: {', '.join(job_offer.responsibilities[:5])}"
    )
    questions = [
        "Can you tell me about your relevant experience?",
        "What interests you about this role?",
        "How do your skills align with the responsibilities?",
    ]
    if candidate and candidate.skills:
        skills_preview = ", ".join(candidate.skills[:3])
        questions.insert(1, f"How have you applied {skills_preview} in your work?")
    _call_prompts[str(event.application_id)] = CallPromptData(
        prepared_questions=questions,
        role_context=role_context,
    )


def generate_call_prompt(event: JobOfferApplied) -> None:
    app_id_str = str(event.application_id)
    last_error = None
    for attempt in range(_PROMPT_RETRIES):
        try:
            _generate_call_prompt_once(event)
            if get_call_prompt(app_id_str) is not None:
                return
        except Exception as e:
            last_error = e
            logger.warning("Call prompt attempt %s failed: %s", attempt + 1, e)
            if attempt < _PROMPT_RETRIES - 1:
                time.sleep(_PROMPT_BACKOFF_BASE * (2 ** attempt))
    logger.warning(
        "Call prompt failed after %s attempts; using minimal default for application %s",
        _PROMPT_RETRIES,
        app_id_str,
        exc_info=last_error,
    )
    _minimal_prompt_for_application(app_id_str)
