"""
Integration tests: event publish and subscribe (Phase 2 Testing Strategy).
In-process event publisher; assert JobOfferApplied is received by subscriber.
"""
import pytest
from src.screening.applications.domain.events import JobOfferApplied
from src.screening.applications.infrastructure.adapters.in_memory_event_publisher import (
    InMemoryEventPublisher,
)
from src.screening.shared.domain import ApplicationId, CandidateId, JobOfferId
from datetime import datetime


@pytest.fixture
def publisher():
    return InMemoryEventPublisher()


def test_publish_job_offer_applied_invokes_subscriber(publisher):
    received = []

    def handler(event):
        received.append(event)

    publisher.subscribe(handler)
    event = JobOfferApplied(
        candidate_id=CandidateId("00000000-0000-0000-0000-000000000001"),
        job_offer_id=JobOfferId("00000000-0000-0000-0000-000000000002"),
        application_id=ApplicationId("00000000-0000-0000-0000-000000000003"),
        occurred_at=datetime.utcnow(),
    )
    publisher.publish(event)
    assert len(received) == 1
    assert received[0] == event
    assert received[0].application_id == event.application_id


def test_publish_multiple_subscribers_both_receive(publisher):
    first = []
    second = []

    def h1(e):
        first.append(e)

    def h2(e):
        second.append(e)

    publisher.subscribe(h1)
    publisher.subscribe(h2)
    event = JobOfferApplied(
        candidate_id=CandidateId("00000000-0000-0000-0000-000000000001"),
        job_offer_id=JobOfferId("00000000-0000-0000-0000-000000000002"),
        application_id=ApplicationId("00000000-0000-0000-0000-000000000003"),
        occurred_at=datetime.utcnow(),
    )
    publisher.publish(event)
    assert len(first) == 1
    assert len(second) == 1
    assert first[0].application_id == second[0].application_id
