from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select

from src.screening.applications.infrastructure.adapters.outbox_repository import (
    OutboxEventRecord,
    OutboxRepository,
)
from src.screening.persistence.models import OutboxEventModel


def _to_record(row: OutboxEventModel) -> OutboxEventRecord:
    payload = row.payload if isinstance(row.payload, dict) else {}
    return OutboxEventRecord(
        id=row.id,
        event_type=row.event_type,
        payload=payload,
        attempts=int(row.attempts or 0),
        created_at=row.created_at,
        last_error=row.last_error,
    )


class PostgresOutboxRepository(OutboxRepository):
    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    def save_pending(self, event_type: str, payload: dict) -> UUID:
        with self._session_factory() as session:
            event_id = uuid4()
            row = OutboxEventModel(
                id=event_id,
                event_type=event_type,
                payload=payload,
                attempts=0,
                created_at=datetime.utcnow(),
                published_at=None,
                last_error=None,
            )
            session.add(row)
            session.commit()
            return event_id

    def list_pending(self, limit: int = 100) -> list[OutboxEventRecord]:
        with self._session_factory() as session:
            rows = (
                session.execute(
                    select(OutboxEventModel)
                    .where(OutboxEventModel.published_at.is_(None))
                    .order_by(OutboxEventModel.created_at.asc())
                    .limit(limit)
                )
                .scalars()
                .all()
            )
            return [_to_record(r) for r in rows]

    def mark_published(self, event_id: UUID) -> None:
        with self._session_factory() as session:
            row = session.get(OutboxEventModel, event_id)
            if row is None:
                return
            row.published_at = datetime.utcnow()
            row.last_error = None
            session.commit()

    def mark_failed_attempt(self, event_id: UUID, error: str) -> None:
        with self._session_factory() as session:
            row = session.get(OutboxEventModel, event_id)
            if row is None:
                return
            row.attempts = int(row.attempts or 0) + 1
            row.last_error = (error or "")[:1000] or None
            session.commit()
