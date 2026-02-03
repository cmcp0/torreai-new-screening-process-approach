from dataclasses import dataclass


@dataclass
class CandidateFromTorre:
    username: str
    full_name: str
    skills: list[str]
    jobs: list[dict]


@dataclass
class JobOfferFromTorre:
    external_id: str
    objective: str
    strengths: list[str]
    responsibilities: list[str]
