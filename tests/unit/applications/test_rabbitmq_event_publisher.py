from datetime import datetime

import pytest

from src.screening.applications.domain.events import JobOfferApplied
from src.screening.applications.infrastructure.adapters.rabbitmq_event_publisher import (
    RabbitMQEventPublisher,
)
from src.screening.shared.domain import ApplicationId, CandidateId, JobOfferId


def _event() -> JobOfferApplied:
    return JobOfferApplied(
        candidate_id=CandidateId("00000000-0000-0000-0000-000000000001"),
        job_offer_id=JobOfferId("00000000-0000-0000-0000-000000000002"),
        application_id=ApplicationId("00000000-0000-0000-0000-000000000003"),
        occurred_at=datetime.utcnow(),
    )


def test_dispatch_runs_all_handlers_and_raises_when_any_fails():
    publisher = RabbitMQEventPublisher("amqp://guest:guest@localhost:5672/%2F")
    events_seen = []

    def failing_handler(event):
        events_seen.append("failing")
        raise RuntimeError("boom")

    def success_handler(event):
        events_seen.append("success")

    publisher.subscribe(failing_handler)
    publisher.subscribe(success_handler)

    with pytest.raises(RuntimeError):
        publisher._dispatch(_event())

    assert events_seen == ["failing", "success"]
