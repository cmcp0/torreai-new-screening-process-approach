from datetime import datetime
from threading import Lock
from uuid import UUID, uuid4

from src.screening.applications.infrastructure.adapters.outbox_repository import (
    OutboxEventRecord,
    OutboxRepository,
)


class InMemoryOutboxRepository(OutboxRepository):
    def __init__(self) -> None:
        self._by_id: dict[UUID, OutboxEventRecord] = {}
        self._published: set[UUID] = set()
        self._lock = Lock()

    def save_pending(self, event_type: str, payload: dict) -> UUID:
        with self._lock:
            event_id = uuid4()
            self._by_id[event_id] = OutboxEventRecord(
                id=event_id,
                event_type=event_type,
                payload=payload,
                attempts=0,
                created_at=datetime.utcnow(),
                last_error=None,
            )
            return event_id

    def list_pending(self, limit: int = 100) -> list[OutboxEventRecord]:
        with self._lock:
            rows = [
                record
                for event_id, record in self._by_id.items()
                if event_id not in self._published
            ]
            rows.sort(key=lambda r: r.created_at)
            return rows[:limit]

    def mark_published(self, event_id: UUID) -> None:
        with self._lock:
            self._published.add(event_id)

    def mark_failed_attempt(self, event_id: UUID, error: str) -> None:
        with self._lock:
            row = self._by_id.get(event_id)
            if row is None:
                return
            self._by_id[event_id] = OutboxEventRecord(
                id=row.id,
                event_type=row.event_type,
                payload=row.payload,
                attempts=row.attempts + 1,
                created_at=row.created_at,
                last_error=error[:1000] if error else None,
            )
