from abc import ABC, abstractmethod
from typing import Optional

from src.screening.analysis.domain.entities import ScreeningAnalysis
from src.screening.shared.domain import ApplicationId, AnalysisId


class AnalysisRepository(ABC):
    @abstractmethod
    def save(self, analysis: ScreeningAnalysis) -> None:
        pass

    @abstractmethod
    def get_by_application(self, application_id: ApplicationId) -> Optional[ScreeningAnalysis]:
        pass

    @abstractmethod
    def upsert_by_application(self, analysis: ScreeningAnalysis) -> None:
        pass
