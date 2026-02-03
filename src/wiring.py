"""
Composition root: service and repository wiring for the screening bounded context.
No framework (FastAPI) here; used by apps/backend and by in-process subscribers.
"""
from typing import TYPE_CHECKING, Any, Optional

from src.config import Settings
from src.screening.applications.application.services import ApplicationService
from src.screening.applications.domain.ports import (
    EventPublisher,
    TorreBiosPort,
    TorreOpportunitiesPort,
)
from src.screening.applications.application.ports import ApplicationRepository
from src.screening.applications.infrastructure.adapters.in_memory_application_repository import (
    InMemoryApplicationRepository,
)
from src.screening.applications.infrastructure.adapters.in_memory_event_publisher import (
    InMemoryEventPublisher,
)
from src.screening.applications.infrastructure.adapters.torre_bios_adapter import (
    TorreBiosAdapter,
)
from src.screening.applications.infrastructure.adapters.torre_opportunities_adapter import (
    TorreOpportunitiesAdapter,
)

if TYPE_CHECKING:
    from src.screening.analysis.application.ports import AnalysisRepository
    from src.screening.calls.application.services import CallService
    from src.screening.analysis.application.services import AnalysisService

_settings: Optional[Settings] = None
_application_service: Optional[ApplicationService] = None
_event_publisher: Optional[InMemoryEventPublisher] = None
_application_repository: Optional[InMemoryApplicationRepository] = None
_call_repository: Optional[Any] = None
_analysis_repository: Optional[Any] = None
_call_service: Optional[Any] = None
_analysis_service: Optional[Any] = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def get_event_publisher() -> EventPublisher:
    global _event_publisher
    if _event_publisher is None:
        _event_publisher = InMemoryEventPublisher()
        _register_subscribers(_event_publisher)
    return _event_publisher


def _register_subscribers(publisher: InMemoryEventPublisher) -> None:
    from src.screening.applications.infrastructure.subscribers import (
        on_job_offer_applied,
    )
    from src.shared.domain.events import DomainEvent
    from src.screening.applications.domain.events import JobOfferApplied

    def dispatch(event: DomainEvent) -> None:
        if isinstance(event, JobOfferApplied):
            on_job_offer_applied(event)

    publisher.subscribe(dispatch)
    try:
        from src.screening.calls.infrastructure.subscribers import (
            on_call_finished,
        )
        from src.screening.calls.domain.events import CallFinished

        def dispatch_call(event: DomainEvent) -> None:
            if isinstance(event, CallFinished):
                on_call_finished(event)

        publisher.subscribe(dispatch_call)
    except ImportError:
        pass


def get_application_repository() -> ApplicationRepository:
    global _application_repository
    if _application_repository is None:
        _application_repository = InMemoryApplicationRepository()
    return _application_repository


def get_app_application_service() -> ApplicationService:
    global _application_service
    if _application_service is None:
        s = get_settings()
        bios: TorreBiosPort = TorreBiosAdapter(
            base_url=s.torre_base_url,
            timeout=s.torre_timeout,
            retries=s.torre_retries,
        )
        opportunities: TorreOpportunitiesPort = TorreOpportunitiesAdapter(
            base_url=s.torre_base_url,
            timeout=s.torre_timeout,
            retries=s.torre_retries,
        )
        repo = get_application_repository()
        pub = get_event_publisher()
        _application_service = ApplicationService(
            bios=bios,
            opportunities=opportunities,
            repository=repo,
            event_publisher=pub,
        )
    return _application_service


def _get_call_prompt(application_id: str):
    from src.screening.applications.infrastructure.subscribers.call_prompt import (
        get_call_prompt as _get,
    )
    return _get(application_id)


def get_call_repository():
    global _call_repository
    if _call_repository is None:
        from src.screening.calls.infrastructure.adapters.in_memory_call_repository import (
            InMemoryCallRepository,
        )
        _call_repository = InMemoryCallRepository()
    return _call_repository


def get_analysis_repository():
    global _analysis_repository
    if _analysis_repository is None:
        from src.screening.analysis.infrastructure.adapters.in_memory_analysis_repository import (
            InMemoryAnalysisRepository,
        )
        _analysis_repository = InMemoryAnalysisRepository()
    return _analysis_repository


def get_call_service():
    global _call_service
    if _call_service is None:
        from src.screening.calls.application.services import CallService
        _call_service = CallService(
            get_call_prompt=_get_call_prompt,
            get_event_publisher=get_event_publisher,
            get_call_repository=get_call_repository,
        )
    return _call_service


def get_emma_service():
    from src.screening.calls.application.services import EmmaService
    return EmmaService()


def get_analysis_service():
    global _analysis_service
    if _analysis_service is None:
        from src.screening.analysis.application.services import AnalysisService
        _analysis_service = AnalysisService(
            get_call_repository=get_call_repository,
            get_application_repository=get_application_repository,
            get_embeddings=None,
            analysis_repository=get_analysis_repository(),
        )
    return _analysis_service
