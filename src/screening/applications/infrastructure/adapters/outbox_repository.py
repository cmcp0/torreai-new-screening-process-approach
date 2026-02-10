from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional
from uuid import UUID


@dataclass(frozen=True)
class OutboxEventRecord:
    id: UUID
    event_type: str
    payload: dict[str, Any]
    attempts: int
    created_at: datetime
    last_error: Optional[str]


class OutboxRepository(ABC):
    @abstractmethod
    def save_pending(self, event_type: str, payload: dict[str, Any]) -> UUID:
        pass

    @abstractmethod
    def list_pending(self, limit: int = 100) -> list[OutboxEventRecord]:
        pass

    @abstractmethod
    def mark_published(self, event_id: UUID) -> None:
        pass

    @abstractmethod
    def mark_failed_attempt(self, event_id: UUID, error: str) -> None:
        pass
