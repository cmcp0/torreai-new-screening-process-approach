from datetime import datetime

import pytest

from src.screening.applications.domain.events import JobOfferApplied
from src.screening.applications.infrastructure.adapters.in_memory_outbox_repository import (
    InMemoryOutboxRepository,
)
from src.screening.applications.infrastructure.adapters.reliable_event_publisher import (
    ReliableEventPublisher,
)
from src.screening.shared.domain import ApplicationId, CandidateId, JobOfferId


def _event() -> JobOfferApplied:
    return JobOfferApplied(
        candidate_id=CandidateId("00000000-0000-0000-0000-000000000001"),
        job_offer_id=JobOfferId("00000000-0000-0000-0000-000000000002"),
        application_id=ApplicationId("00000000-0000-0000-0000-000000000003"),
        occurred_at=datetime.utcnow(),
    )


def test_reliable_publisher_marks_event_published_on_success():
    class DelegatePublisher:
        def __init__(self) -> None:
            self.events = []
            self.handlers = []

        def subscribe(self, handler):
            self.handlers.append(handler)

        def publish(self, event):
            self.events.append(event)

    outbox = InMemoryOutboxRepository()
    delegate = DelegatePublisher()
    publisher = ReliableEventPublisher(delegate=delegate, outbox_repository=outbox)

    event = _event()
    publisher.publish(event)

    assert len(delegate.events) == 1
    assert delegate.events[0] == event
    assert outbox.list_pending() == []


def test_reliable_publisher_replays_pending_after_temporary_failure():
    class FlakyDelegatePublisher:
        def __init__(self) -> None:
            self.events = []
            self._first = True
            self.handlers = []

        def subscribe(self, handler):
            self.handlers.append(handler)

        def publish(self, event):
            if self._first:
                self._first = False
                raise RuntimeError("temporary broker outage")
            self.events.append(event)

    outbox = InMemoryOutboxRepository()
    delegate = FlakyDelegatePublisher()
    publisher = ReliableEventPublisher(delegate=delegate, outbox_repository=outbox)

    event = _event()
    with pytest.raises(RuntimeError):
        publisher.publish(event)

    pending_after_failure = outbox.list_pending()
    assert len(pending_after_failure) == 1
    assert pending_after_failure[0].attempts == 1

    publisher._drain_pending_once(limit=10)  # intentional white-box check for retry path

    assert outbox.list_pending() == []
    assert len(delegate.events) == 1
    assert delegate.events[0] == event
