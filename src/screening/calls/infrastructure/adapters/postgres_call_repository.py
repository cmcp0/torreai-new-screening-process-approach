from src.screening.calls.application.ports import CallRepository
from src.screening.calls.domain.entities import ScreeningCall, TranscriptSegment
from src.screening.calls.domain.value_objects import CallStatus
from src.screening.persistence.models import CallModel
from src.screening.shared.domain import ApplicationId, CallId


def _segment_to_dict(seg: TranscriptSegment) -> dict:
    return {"speaker": seg.speaker, "text": seg.text, "timestamp": seg.timestamp}


def _dict_to_segment(d: dict) -> TranscriptSegment:
    return TranscriptSegment(
        speaker=d.get("speaker", ""),
        text=d.get("text", ""),
        timestamp=float(d.get("timestamp", 0)),
    )


def _row_to_call(row: CallModel) -> ScreeningCall:
    transcript = [
        _dict_to_segment(seg) for seg in (row.transcript if isinstance(row.transcript, list) else [])
    ]
    return ScreeningCall(
        id=CallId(row.id),
        application_id=ApplicationId(row.application_id),
        status=CallStatus(row.status),
        started_at=row.started_at,
        ended_at=row.ended_at,
        transcript=transcript,
    )


class PostgresCallRepository(CallRepository):
    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    def save_call(self, call: ScreeningCall) -> None:
        with self._session_factory() as session:
            row = CallModel(
                id=call.id.value,
                application_id=call.application_id.value,
                status=call.status.value,
                started_at=call.started_at,
                ended_at=call.ended_at,
                transcript=[_segment_to_dict(s) for s in call.transcript],
            )
            session.merge(row)
            session.commit()

    def get_call(self, call_id: CallId) -> ScreeningCall | None:
        with self._session_factory() as session:
            row = session.get(CallModel, call_id.value)
            return _row_to_call(row) if row else None

    def update_call_transcript(
        self, call_id: CallId, transcript: list[TranscriptSegment]
    ) -> None:
        with self._session_factory() as session:
            row = session.get(CallModel, call_id.value)
            if row:
                row.transcript = [_segment_to_dict(s) for s in transcript]
                session.commit()

    def mark_call_completed(self, call_id: CallId) -> None:
        from datetime import datetime
        with self._session_factory() as session:
            row = session.get(CallModel, call_id.value)
            if row:
                row.status = CallStatus.COMPLETED.value
                row.ended_at = datetime.utcnow()
                session.commit()
