from abc import ABC, abstractmethod

from src.shared.domain.events import DomainEvent


class EventPublisher(ABC):
    @abstractmethod
    def publish(self, event: DomainEvent) -> None:
        pass
