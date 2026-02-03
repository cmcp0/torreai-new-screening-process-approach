from typing import Optional

from src.screening.analysis.domain.entities import ScreeningAnalysis
from src.screening.analysis.application.ports import AnalysisRepository
from src.screening.shared.domain import ApplicationId


class InMemoryAnalysisRepository(AnalysisRepository):
    def __init__(self) -> None:
        self._by_application = {}

    def save(self, analysis: ScreeningAnalysis) -> None:
        self._by_application[str(analysis.application_id)] = analysis

    def get_by_application(self, application_id: ApplicationId) -> Optional[ScreeningAnalysis]:
        return self._by_application.get(str(application_id))

    def upsert_by_application(self, analysis: ScreeningAnalysis) -> None:
        self._by_application[str(analysis.application_id)] = analysis
