import logging
from dataclasses import dataclass
from typing import Optional

from src.screening.applications.domain.events import JobOfferApplied

logger = logging.getLogger(__name__)

_call_prompts = {}


@dataclass
class CallPromptData:
    prepared_questions: list
    role_context: str


def get_call_prompt(application_id: str) -> Optional[CallPromptData]:
    return _call_prompts.get(application_id)


def generate_call_prompt(event: JobOfferApplied) -> None:
    from src.screening.applications.application.ports import ApplicationRepository
    from src.wiring import get_application_repository

    repo: ApplicationRepository = get_application_repository()
    app = repo.get_application(event.application_id)
    if app is None:
        return
    if not hasattr(repo, "get_job_offer") or not hasattr(repo, "get_candidate"):
        _call_prompts[str(event.application_id)] = CallPromptData(
            prepared_questions=["Tell me about your background."],
            role_context="Screening call.",
        )
        return
    job_offer = repo.get_job_offer(event.job_offer_id)
    candidate = repo.get_candidate(event.candidate_id)
    if job_offer is None:
        _call_prompts[str(event.application_id)] = CallPromptData(
            prepared_questions=["Tell me about your background."],
            role_context="Screening call.",
        )
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
        questions.insert(1, f"Your profile mentions skills like {', '.join(candidate.skills[:3])}. How have you applied them?")
    _call_prompts[str(event.application_id)] = CallPromptData(
        prepared_questions=questions,
        role_context=role_context,
    )
