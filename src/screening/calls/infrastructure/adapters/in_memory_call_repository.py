from typing import Optional

from src.screening.calls.domain.entities import (
    ScreeningCall,
    TranscriptSegment,
)
from src.screening.calls.domain.value_objects import CallStatus
from src.screening.calls.application.ports import CallRepository
from src.screening.shared.domain import CallId


class InMemoryCallRepository(CallRepository):
    def __init__(self) -> None:
        self._calls: dict[str, ScreeningCall] = {}

    def save_call(self, call: ScreeningCall) -> None:
        self._calls[str(call.id)] = call

    def get_call(self, call_id: CallId) -> Optional[ScreeningCall]:
        return self._calls.get(str(call_id))

    def update_call_transcript(
        self, call_id: CallId, transcript: list[TranscriptSegment]
    ) -> None:
        call = self._calls.get(str(call_id))
        if call:
            call.transcript.clear()
            call.transcript.extend(transcript)

    def mark_call_completed(self, call_id: CallId) -> None:
        call = self._calls.get(str(call_id))
        if call:
            from datetime import datetime
            call.ended_at = datetime.utcnow()
            call.status = CallStatus.COMPLETED
