from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from src.screening.shared.domain import ApplicationId, CallId
from src.screening.calls.domain.value_objects import CallStatus


@dataclass
class TranscriptSegment:
    speaker: str
    text: str
    timestamp: float


@dataclass
class ScreeningCall:
    id: CallId
    application_id: ApplicationId
    status: CallStatus
    started_at: datetime
    ended_at: Optional[datetime]
    transcript: list
