import logging
from typing import Callable

from src.shared.domain.events import DomainEvent
from src.screening.applications.domain.ports import EventPublisher

logger = logging.getLogger(__name__)


class InMemoryEventPublisher(EventPublisher):
    def __init__(self) -> None:
        self._handlers: list[Callable[[DomainEvent], None]] = []

    def subscribe(self, handler: Callable[[DomainEvent], None]) -> None:
        self._handlers.append(handler)

    def publish(self, event: DomainEvent) -> None:
        for handler in self._handlers:
            try:
                handler(event)
            except Exception as e:
                logger.exception("Event handler failed: %s", e)
