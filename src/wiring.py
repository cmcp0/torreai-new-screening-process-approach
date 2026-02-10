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
from src.screening.applications.infrastructure.adapters.in_memory_outbox_repository import (
    InMemoryOutboxRepository,
)
from src.screening.applications.infrastructure.adapters.rabbitmq_event_publisher import (
    RabbitMQEventPublisher,
)
from src.screening.applications.infrastructure.adapters.reliable_event_publisher import (
    ReliableEventPublisher,
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
_event_publisher: Optional[EventPublisher] = None
_application_repository: Optional[Any] = None
_embedding_repository: Optional[Any] = None
_outbox_repository: Optional[Any] = None
_call_repository: Optional[Any] = None
_analysis_repository: Optional[Any] = None
_call_service: Optional[Any] = None
_analysis_service: Optional[Any] = None
_persistence_session_factory: Optional[Any] = None
_audio_transcriber: Optional[Any] = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def get_event_publisher() -> EventPublisher:
    global _event_publisher
    if _event_publisher is None:
        s = get_settings()
        if s.broker_url:
            base_pub = RabbitMQEventPublisher(s.broker_url)
            reliable_pub = ReliableEventPublisher(
                delegate=base_pub,
                outbox_repository=get_outbox_repository(),
            )
            _register_subscribers(reliable_pub)
            base_pub.start_consumer()
            reliable_pub.start_relay()
            _event_publisher = reliable_pub
        else:
            pub = InMemoryEventPublisher()
            _register_subscribers(pub)
            _event_publisher = pub
    return _event_publisher


def _register_subscribers(
    publisher: EventPublisher,
) -> None:
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


def _get_persistence_session_factory():
    global _persistence_session_factory
    s = get_settings()
    if not s.database_url:
        return None
    if _persistence_session_factory is None:
        from src.screening.persistence.models import (
            Base,
            create_engine_from_url,
            get_session_factory,
        )
        engine = create_engine_from_url(s.database_url)
        Base.metadata.create_all(engine)
        _persistence_session_factory = get_session_factory(engine)
    return _persistence_session_factory


def get_application_repository() -> ApplicationRepository:
    global _application_repository
    if _application_repository is None:
        session_factory = _get_persistence_session_factory()
        if session_factory is not None:
            from src.screening.applications.infrastructure.adapters.postgres_application_repository import (
                PostgresApplicationRepository,
            )
            _application_repository = PostgresApplicationRepository(session_factory)
        else:
            _application_repository = InMemoryApplicationRepository()
    return _application_repository


def get_embedding_repository():
    global _embedding_repository
    if _embedding_repository is None:
        session_factory = _get_persistence_session_factory()
        if session_factory is not None:
            from src.screening.applications.application.ports import EmbeddingRepository
            from src.screening.applications.infrastructure.adapters.postgres_embedding_repository import (
                PostgresEmbeddingRepository,
            )
            _embedding_repository = PostgresEmbeddingRepository(session_factory)
        else:
            from src.screening.applications.infrastructure.adapters.in_memory_embedding_repository import (
                InMemoryEmbeddingRepository,
            )
            _embedding_repository = InMemoryEmbeddingRepository()
    return _embedding_repository


def get_outbox_repository():
    global _outbox_repository
    if _outbox_repository is None:
        session_factory = _get_persistence_session_factory()
        if session_factory is not None:
            from src.screening.applications.infrastructure.adapters.postgres_outbox_repository import (
                PostgresOutboxRepository,
            )

            _outbox_repository = PostgresOutboxRepository(session_factory)
        else:
            _outbox_repository = InMemoryOutboxRepository()
    return _outbox_repository


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
        session_factory = _get_persistence_session_factory()
        if session_factory is not None:
            from src.screening.calls.infrastructure.adapters.postgres_call_repository import (
                PostgresCallRepository,
            )
            _call_repository = PostgresCallRepository(session_factory)
        else:
            from src.screening.calls.infrastructure.adapters.in_memory_call_repository import (
                InMemoryCallRepository,
            )
            _call_repository = InMemoryCallRepository()
    return _call_repository


def get_analysis_repository():
    global _analysis_repository
    if _analysis_repository is None:
        session_factory = _get_persistence_session_factory()
        if session_factory is not None:
            from src.screening.analysis.infrastructure.adapters.postgres_analysis_repository import (
                PostgresAnalysisRepository,
            )
            _analysis_repository = PostgresAnalysisRepository(session_factory)
        else:
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
    from src.screening.calls.infrastructure.adapters.ollama_llm import ollama_chat
    s = get_settings()
    if (s.ollama_base_url or "").strip():
        return EmmaService(llm_generate=ollama_chat)
    return EmmaService()


def get_audio_transcriber():
    """
    Returns the audio transcriber callable used by the websocket handler.
    Uses the shared adapter `transcribe_audio`, with default settings (no STT base URL configured).
    """
    global _audio_transcriber
    if _audio_transcriber is None:
        from functools import partial
        from src.screening.calls.infrastructure.adapters.audio_transcriber import transcribe_audio

        # Default arguments are kept empty; environment configuration can be added to Settings later.
        _audio_transcriber = partial(transcribe_audio)
    return _audio_transcriber


def get_analysis_service():
    global _analysis_service
    if _analysis_service is None:
        from src.screening.analysis.application.services import AnalysisService
        from src.screening.applications.infrastructure.subscribers.embeddings import (
            get_candidate_embeddings,
            get_job_offer_embeddings,
        )

        def _get_embeddings(candidate_id_str: str, job_offer_id_str: str):
            repo = get_embedding_repository()
            c = repo.get_candidate_embedding(candidate_id_str) if repo else None
            j = repo.get_job_offer_embedding(job_offer_id_str) if repo else None
            if c is None:
                c = get_candidate_embeddings(candidate_id_str)
            if j is None:
                j = get_job_offer_embeddings(job_offer_id_str)
            return (c, j)

        _analysis_service = AnalysisService(
            get_call_repository=get_call_repository,
            get_application_repository=get_application_repository,
            get_embeddings=_get_embeddings,
            analysis_repository=get_analysis_repository(),
            event_publisher=get_event_publisher(),
        )
    return _analysis_service
