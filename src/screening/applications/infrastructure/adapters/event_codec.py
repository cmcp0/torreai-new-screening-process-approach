import json
from datetime import datetime
from typing import Any, Mapping

from src.screening.analysis.domain.events import AnalysisCompleted
from src.screening.applications.domain.events import JobOfferApplied
from src.screening.calls.domain.events import CallFinished
from src.screening.shared.domain import (
    AnalysisId,
    ApplicationId,
    CallId,
    CandidateId,
    JobOfferId,
)
from src.shared.domain.events import DomainEvent


def event_to_envelope(event: DomainEvent) -> dict[str, Any]:
    if isinstance(event, JobOfferApplied):
        return {
            "type": "JobOfferApplied",
            "payload": {
                "occurred_at": event.occurred_at.isoformat(),
                "candidate_id": str(event.candidate_id),
                "job_offer_id": str(event.job_offer_id),
                "application_id": str(event.application_id),
            },
        }
    if isinstance(event, CallFinished):
        return {
            "type": "CallFinished",
            "payload": {
                "occurred_at": event.occurred_at.isoformat(),
                "application_id": str(event.application_id),
                "call_id": str(event.call_id),
            },
        }
    if isinstance(event, AnalysisCompleted):
        return {
            "type": "AnalysisCompleted",
            "payload": {
                "occurred_at": event.occurred_at.isoformat(),
                "application_id": str(event.application_id),
                "analysis_id": str(event.analysis_id),
            },
        }
    raise ValueError(f"Unsupported event type: {type(event)}")


def envelope_to_event(envelope: Mapping[str, Any]) -> DomainEvent:
    event_type = envelope.get("type")
    payload = envelope.get("payload", {})
    if not isinstance(payload, Mapping):
        raise ValueError("Invalid event payload")

    if event_type == "JobOfferApplied":
        return JobOfferApplied(
            occurred_at=datetime.fromisoformat(str(payload["occurred_at"])),
            candidate_id=CandidateId(str(payload["candidate_id"])),
            job_offer_id=JobOfferId(str(payload["job_offer_id"])),
            application_id=ApplicationId(str(payload["application_id"])),
        )
    if event_type == "CallFinished":
        return CallFinished(
            occurred_at=datetime.fromisoformat(str(payload["occurred_at"])),
            application_id=ApplicationId(str(payload["application_id"])),
            call_id=CallId(str(payload["call_id"])),
        )
    if event_type == "AnalysisCompleted":
        return AnalysisCompleted(
            occurred_at=datetime.fromisoformat(str(payload["occurred_at"])),
            application_id=ApplicationId(str(payload["application_id"])),
            analysis_id=AnalysisId(str(payload["analysis_id"])),
        )
    raise ValueError(f"Unknown event type: {event_type}")


def serialize_event(event: DomainEvent) -> bytes:
    return json.dumps(event_to_envelope(event)).encode("utf-8")


def deserialize_event(body: bytes) -> DomainEvent:
    data = json.loads(body.decode("utf-8"))
    if not isinstance(data, Mapping):
        raise ValueError("Invalid event envelope")
    return envelope_to_event(data)
