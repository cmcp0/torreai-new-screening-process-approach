from abc import ABC, abstractmethod
from typing import Optional

from src.screening.calls.domain.entities import ScreeningCall, TranscriptSegment
from src.screening.shared.domain import CallId


class CallRepository(ABC):
    @abstractmethod
    def save_call(self, call: ScreeningCall) -> None:
        pass

    @abstractmethod
    def get_call(self, call_id: CallId) -> Optional[ScreeningCall]:
        pass

    @abstractmethod
    def update_call_transcript(
        self, call_id: CallId, transcript: list[TranscriptSegment]
    ) -> None:
        pass

    @abstractmethod
    def mark_call_completed(self, call_id: CallId) -> None:
        pass
