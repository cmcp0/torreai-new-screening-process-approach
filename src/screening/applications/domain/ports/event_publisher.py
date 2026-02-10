from abc import ABC, abstractmethod
from typing import Callable

from src.shared.domain.events import DomainEvent


class EventPublishError(Exception):
    """Raised when a domain event cannot be published by the current adapter."""


class EventPublisher(ABC):
    @abstractmethod
    def subscribe(self, handler: Callable[[DomainEvent], None]) -> None:
        pass

    @abstractmethod
    def publish(self, event: DomainEvent) -> None:
        pass
