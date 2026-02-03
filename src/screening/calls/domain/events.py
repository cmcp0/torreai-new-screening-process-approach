from dataclasses import dataclass
from datetime import datetime

from src.shared.domain.events import DomainEvent
from src.screening.shared.domain import ApplicationId, CallId


@dataclass(frozen=True)
class CallFinished(DomainEvent):
    application_id: ApplicationId
    call_id: CallId
