from dataclasses import dataclass
from datetime import datetime

from src.shared.domain.events import DomainEvent
from src.screening.shared.domain import ApplicationId, CandidateId, JobOfferId


@dataclass(frozen=True)
class JobOfferApplied(DomainEvent):
    candidate_id: CandidateId
    job_offer_id: JobOfferId
    application_id: ApplicationId
