from dataclasses import dataclass
from datetime import datetime

from src.screening.shared.domain import AnalysisId, ApplicationId


@dataclass
class ScreeningAnalysis:
    id: AnalysisId
    application_id: ApplicationId
    fit_score: int
    skills: list[str]
    completed_at: datetime
    status: str = "completed"  # "completed" | "failed"
