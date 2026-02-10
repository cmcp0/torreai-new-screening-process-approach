"""
Integration tests: WebSocket handshake and message flow (Phase 2 Testing Strategy).
Stub client connects to /api/ws/call, receives greeting/control, sends text, receives question.
"""
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from apps.backend.main import app
from apps.backend.routes.applications import get_application_service
from src.screening.applications.application.services import ApplicationService
from src.screening.applications.domain.value_objects import (
    CandidateFromTorre,
    JobOfferFromTorre,
)
from src.screening.applications.infrastructure.adapters.in_memory_application_repository import (
    InMemoryApplicationRepository,
)
from src.screening.applications.infrastructure.adapters.in_memory_event_publisher import (
    InMemoryEventPublisher,
)


class MockBios:
    async def get_bio(self, username):
        return CandidateFromTorre(
            username=username, full_name="Test", skills=[], jobs=[],
        )


class MockOpportunities:
    async def get_opportunity(self, job_offer_id):
        return JobOfferFromTorre(
            external_id=job_offer_id, objective="X", strengths=[], responsibilities=[],
        )


@pytest.fixture
def client_with_app():
    from apps.backend.routes.applications import get_application_service
    repo = InMemoryApplicationRepository()
    pub = InMemoryEventPublisher()
    svc = ApplicationService(
        bios=MockBios(),
        opportunities=MockOpportunities(),
        repository=repo,
        event_publisher=pub,
    )
    app.dependency_overrides[get_application_service] = lambda: svc
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_application_service, None)


def test_websocket_handshake_and_message_flow(client_with_app):
    r = client_with_app.post("/api/applications", json={"username": "wsuser", "job_offer_id": "wsjob"})
    assert r.status_code == 201
    application_id = r.json()["application_id"]
    with client_with_app.websocket_connect(
        f"/api/ws/call?application_id={application_id}"
    ) as ws:
        msg = ws.receive_json()
        assert msg.get("type") == "control"
        assert msg.get("event") == "emma_speaking"
        msg = ws.receive_json()
        assert msg.get("type") == "text"
        assert "Emma" in msg.get("text", "") or "Hello" in msg.get("text", "")
        msg = ws.receive_json()
        assert msg.get("type") == "control"
        assert msg.get("event") == "listening"
        ws.send_json({"type": "text", "text": "Ready"})
        msg = ws.receive_json()
        assert msg.get("type") in ("control", "text")


def test_websocket_invalid_application_id_rejected(client_with_app):
    with pytest.raises(Exception):
        with client_with_app.websocket_connect(
            "/api/ws/call?application_id=not-a-uuid"
        ) as ws:
            ws.receive_json()


def test_websocket_duplicate_connection_rejected(client_with_app):
    r = client_with_app.post("/api/applications", json={"username": "dup", "job_offer_id": "j1"})
    assert r.status_code == 201
    application_id = r.json()["application_id"]
    with client_with_app.websocket_connect(
        f"/api/ws/call?application_id={application_id}"
    ) as first:
        first.receive_json()
        with pytest.raises(WebSocketDisconnect) as exc:
            with client_with_app.websocket_connect(
                f"/api/ws/call?application_id={application_id}"
            ) as second:
                second.receive_json()
        assert exc.value.code == 4409


def test_websocket_accepts_audio_mode_messages(client_with_app):
    r = client_with_app.post("/api/applications", json={"username": "audio", "job_offer_id": "j2"})
    assert r.status_code == 201
    application_id = r.json()["application_id"]
    with client_with_app.websocket_connect(
        f"/api/ws/call?application_id={application_id}"
    ) as ws:
        ws.receive_json()  # emma_speaking
        ws.receive_json()  # greeting text
        ws.receive_json()  # listening
        ws.send_json({"type": "audio_start", "codec": "webm-opus", "sample_rate_hz": 16000})
        ws.send_json({"type": "audio_chunk", "data_b64": "UmVhZHk=", "seq": 0, "is_final": True})
        # No STT backend is configured in this test process, so we send
        # text fallback to verify dual-protocol compatibility.
        ws.send_json({"type": "text", "text": "Ready"})
        candidate_echo = None
        for _ in range(6):
            msg = ws.receive_json()
            if msg.get("type") == "text" and msg.get("speaker") == "candidate":
                candidate_echo = msg
                break
        assert candidate_echo is not None
        assert "Ready" in candidate_echo.get("text", "")
