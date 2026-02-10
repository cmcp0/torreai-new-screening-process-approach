from typing import Optional

from sqlalchemy import select

from src.screening.analysis.application.ports import AnalysisRepository
from src.screening.analysis.domain.entities import ScreeningAnalysis
from src.screening.persistence.models import AnalysisModel
from src.screening.shared.domain import ApplicationId, AnalysisId


def _row_to_analysis(row: AnalysisModel) -> ScreeningAnalysis:
    skills = row.skills if isinstance(row.skills, list) else []
    return ScreeningAnalysis(
        id=AnalysisId(row.id),
        application_id=ApplicationId(row.application_id),
        fit_score=row.fit_score,
        skills=skills,
        completed_at=row.completed_at,
        status=getattr(row, "status", "completed"),
    )


class PostgresAnalysisRepository(AnalysisRepository):
    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    def save(self, analysis: ScreeningAnalysis) -> None:
        with self._session_factory() as session:
            row = AnalysisModel(
                id=analysis.id.value,
                application_id=analysis.application_id.value,
                fit_score=analysis.fit_score,
                skills=analysis.skills,
                completed_at=analysis.completed_at,
                status=getattr(analysis, "status", "completed"),
            )
            session.merge(row)
            session.commit()

    def get_by_application(self, application_id: ApplicationId) -> Optional[ScreeningAnalysis]:
        with self._session_factory() as session:
            row = (
                session.execute(
                    select(AnalysisModel).where(
                        AnalysisModel.application_id == application_id.value
                    )
                )
                .scalars()
                .first()
            )
            return _row_to_analysis(row) if row else None

    def upsert_by_application(self, analysis: ScreeningAnalysis) -> None:
        with self._session_factory() as session:
            row = (
                session.execute(
                    select(AnalysisModel).where(
                        AnalysisModel.application_id == analysis.application_id.value
                    )
                )
                .scalars()
                .first()
            )
            if row:
                row.fit_score = analysis.fit_score
                row.skills = analysis.skills
                row.completed_at = analysis.completed_at
                row.status = getattr(analysis, "status", "completed")
            else:
                session.add(
                    AnalysisModel(
                        id=analysis.id.value,
                        application_id=analysis.application_id.value,
                        fit_score=analysis.fit_score,
                        skills=analysis.skills,
                        completed_at=analysis.completed_at,
                        status=getattr(analysis, "status", "completed"),
                    )
                )
            session.commit()
