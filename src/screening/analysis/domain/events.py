from dataclasses import dataclass
from datetime import datetime

from src.shared.domain.events import DomainEvent
from src.screening.shared.domain import AnalysisId, ApplicationId


@dataclass(frozen=True)
class AnalysisCompleted(DomainEvent):
    """Published when analysis for an application completes successfully. Consumers may use it for push/SSE or downstream workflows."""
    application_id: ApplicationId
    analysis_id: AnalysisId
