from dataclasses import dataclass


@dataclass
class FitAssessment:
    score: int
    skills: list[str]
