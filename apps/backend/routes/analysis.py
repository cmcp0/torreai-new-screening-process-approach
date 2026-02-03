from fastapi import APIRouter, Depends, HTTPException

from apps.backend.schemas import AnalysisResponse
from src.screening.analysis.application.services import AnalysisService
from src.screening.shared.domain import ApplicationId
from src import wiring

router = APIRouter(tags=["analysis"])


def get_analysis_service() -> AnalysisService:
    return wiring.get_analysis_service()


@router.get(
    "/applications/{application_id}/analysis",
    response_model=AnalysisResponse,
    status_code=200,
    responses={
        200: {"description": "Analysis ready"},
        202: {"description": "Analysis pending"},
        404: {"description": "Application or analysis not found"},
    },
)
async def get_analysis(
    application_id: str,
    service: AnalysisService = Depends(get_analysis_service),
) -> AnalysisResponse:
    try:
        app_id = ApplicationId(application_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=404, detail="Application not found")

    result = await service.get_analysis_for_application(app_id)
    if not result.found_application:
        raise HTTPException(status_code=404, detail="Application not found")
    if result.analysis is None:
        raise HTTPException(status_code=202, detail="Analysis pending")

    return AnalysisResponse(
        fit_score=result.analysis.fit_score,
        skills=result.analysis.skills,
    )
