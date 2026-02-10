import httpx
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from apps.backend.schemas import CreateApplicationRequest, CreateApplicationResponse
from src.screening.applications.application.services import ApplicationService
from src.screening.applications.application.services.application_service import (
    TorreNotFoundError,
)
from src.screening.applications.domain.ports import EventPublishError
from src import wiring

router = APIRouter(prefix="/applications", tags=["applications"])


def get_application_service() -> ApplicationService:
    return wiring.get_app_application_service()


@router.post("", response_model=CreateApplicationResponse, status_code=201)
async def create_application(
    body: Optional[CreateApplicationRequest] = None,
    service: ApplicationService = Depends(get_application_service),
) -> CreateApplicationResponse:
    if body is None:
        raise HTTPException(status_code=400, detail="username and job_offer_id are required")

    try:
        result = await service.create_application(
            username=body.username,
            job_offer_id=body.job_offer_id,
        )
        return CreateApplicationResponse(
            application_id=str(result.application_id),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except EventPublishError:
        raise HTTPException(status_code=503, detail="Event broker unavailable")
    except TorreNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (httpx.TimeoutException, httpx.ConnectError):
        raise HTTPException(status_code=503, detail="Upstream service unavailable")
    except httpx.HTTPStatusError as e:
        if e.response.status_code >= 500:
            raise HTTPException(status_code=502, detail="Upstream service error")
        raise HTTPException(status_code=422, detail="Invalid data from upstream")
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Upstream service unavailable")
