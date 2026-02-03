from dataclasses import dataclass
from datetime import datetime

from src.screening.shared.domain import ApplicationId, CandidateId, JobOfferId


@dataclass
class ScreeningApplication:
    id: ApplicationId
    candidate_id: CandidateId
    job_offer_id: JobOfferId
    created_at: datetime


@dataclass
class Candidate:
    id: CandidateId
    username: str
    full_name: str
    skills: list[str]
    jobs: list[dict]


@dataclass
class JobOffer:
    id: JobOfferId
    external_id: str
    objective: str
    strengths: list[str]
    responsibilities: list[str]
