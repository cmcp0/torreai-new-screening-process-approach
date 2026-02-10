from datetime import datetime
from typing import Callable, Optional, Protocol
from uuid import uuid4

from src.screening.applications.domain.ports import EventPublisher
from src.screening.calls.application.ports import CallRepository
from src.screening.calls.domain.entities import (
    ScreeningCall,
    TranscriptSegment,
)
from src.screening.calls.domain.value_objects import CallStatus
from src.screening.calls.domain.events import CallFinished
from src.screening.shared.domain import ApplicationId, CallId


class CallPrompt:
    def __init__(
        self,
        prepared_questions: list[str],
        role_context: str,
    ) -> None:
        self.prepared_questions = prepared_questions
        self.role_context = role_context


class CallPromptProviderResult(Protocol):
    prepared_questions: list[str]
    role_context: str


class CallService:
    def __init__(
        self,
        get_call_prompt: Callable[[str], Optional[CallPromptProviderResult]],
        get_event_publisher: Callable[[], EventPublisher],
        get_call_repository: Callable[[], Optional[CallRepository]],
    ) -> None:
        self._get_call_prompt = get_call_prompt
        self._get_event_publisher = get_event_publisher
        self._get_call_repository = get_call_repository
        self._active_calls: dict[str, CallId] = {}

    def is_application_in_call(self, application_id: ApplicationId) -> bool:
        return str(application_id) in self._active_calls

    def register_active_call(self, application_id: ApplicationId, call_id: CallId) -> None:
        self._active_calls[str(application_id)] = call_id

    def unregister_active_call(self, application_id: ApplicationId) -> None:
        self._active_calls.pop(str(application_id), None)

    def get_prompt_for_application(self, application_id: ApplicationId) -> Optional[CallPrompt]:
        prompt = self._get_call_prompt(str(application_id))
        if prompt is None:
            return CallPrompt(
                prepared_questions=["Tell me about your background."],
                role_context="Screening call.",
            )
        return CallPrompt(
            prepared_questions=prompt.prepared_questions,
            role_context=prompt.role_context,
        )

    def start_call(self, application_id: ApplicationId) -> ScreeningCall:
        call_id = CallId(uuid4())
        call = ScreeningCall(
            id=call_id,
            application_id=application_id,
            status=CallStatus.IN_PROGRESS,
            started_at=datetime.utcnow(),
            ended_at=None,
            transcript=[],
        )
        repo = self._get_call_repository()
        if repo:
            repo.save_call(call)
        self.register_active_call(application_id, call_id)
        return call

    def end_call(
        self,
        application_id: ApplicationId,
        call_id: CallId,
        transcript: list[TranscriptSegment],
    ) -> None:
        self.unregister_active_call(application_id)
        repo = self._get_call_repository()
        if repo:
            repo.update_call_transcript(call_id, transcript)
            repo.mark_call_completed(call_id)
        event = CallFinished(
            application_id=application_id,
            call_id=call_id,
            occurred_at=datetime.utcnow(),
        )
        publisher = self._get_event_publisher()
        publisher.publish(event)
