import asyncio
import base64

import pytest

from src.screening.calls.infrastructure import websocket_handler


class StubWebSocket:
    def __init__(self, messages=None, block_forever=False):
        self._messages = list(messages or [])
        self._block_forever = block_forever
        self.sent = []

    async def receive_text(self):
        if self._messages:
            return self._messages.pop(0)
        if self._block_forever:
            await asyncio.Future()
        await asyncio.sleep(0)
        return ""

    async def send_json(self, payload):
        self.sent.append(payload)

    async def close(self, code=None, reason=None):
        self.closed = {"code": code, "reason": reason}


@pytest.mark.asyncio
async def test_receive_candidate_text_returns_immediately_when_message_arrives(monkeypatch):
    monkeypatch.setattr(websocket_handler, "_TEXT_CONTINUATION_WINDOW_SECONDS", 0.001)
    ws = StubWebSocket(messages=['{"type":"text","text":"Ready now"}'])
    segments = []

    text = await websocket_handler._receive_candidate_text(
        websocket=ws,
        timeout=0.01,
        retries=2,
        add_segment=lambda speaker, value: segments.append((speaker, value)),
        nudge="Please continue when ready.",
    )

    assert text == "Ready now"
    assert ws.sent == []
    assert segments == []


@pytest.mark.asyncio
async def test_receive_candidate_text_retries_and_nudges_before_returning_none(monkeypatch):
    ws = StubWebSocket(block_forever=True)
    segments = []
    nudge = "I'm still listening. Take your time."

    text = await websocket_handler._receive_candidate_text(
        websocket=ws,
        timeout=0.01,
        retries=2,
        add_segment=lambda speaker, value: segments.append((speaker, value)),
        nudge=nudge,
    )

    assert text is None
    assert segments == [("emma", nudge), ("emma", nudge)]
    assert ws.sent == [
        {"type": "control", "event": "emma_speaking"},
        {"type": "text", "text": nudge, "speaker": "emma"},
        {"type": "control", "event": "listening"},
        {"type": "control", "event": "emma_speaking"},
        {"type": "text", "text": nudge, "speaker": "emma"},
        {"type": "control", "event": "listening"},
    ]


@pytest.mark.asyncio
async def test_receive_candidate_text_ignores_echo_of_emma_and_waits_for_real_answer(monkeypatch):
    monkeypatch.setattr(websocket_handler, "_TEXT_CONTINUATION_WINDOW_SECONDS", 0.001)
    ws = StubWebSocket(
        messages=[
            "{\"type\":\"text\",\"text\":\"Hello! I'm Emma. I'll ask you a few questions about your experience.\"}",
            "{\"type\":\"text\",\"text\":\"I worked with Python for 3 years.\"}",
        ]
    )

    text = await websocket_handler._receive_candidate_text(
        websocket=ws,
        timeout=0.01,
        retries=1,
        add_segment=lambda *_: None,
        nudge="Please continue when ready.",
        last_emma_text="Hello! I'm Emma. I'll ask you a few questions about your experience.",
    )

    assert text == "I worked with Python for 3 years."


@pytest.mark.asyncio
async def test_receive_candidate_text_accepts_audio_messages(monkeypatch):
    monkeypatch.setattr(websocket_handler, "_DEFAULT_READY_TIMEOUT_BASE_SECONDS", 0.01)
    payload = base64.b64encode(b"I have worked with GraphQL.").decode("ascii")
    ws = StubWebSocket(
        messages=[
            '{"type":"audio_start","codec":"webm-opus","sample_rate_hz":48000}',
            f'{{"type":"audio_chunk","data_b64":"{payload}","seq":0,"is_final":true}}',
        ]
    )

    async def fake_transcriber(chunks, codec, sample_rate_hz):
        assert codec == "webm-opus"
        assert sample_rate_hz == 48000
        return b"".join(chunks).decode("utf-8")

    text = await websocket_handler._receive_candidate_text(
        websocket=ws,
        timeout=0.01,
        retries=1,
        add_segment=lambda *_: None,
        nudge="Please continue when ready.",
        transcribe_audio=fake_transcriber,
    )

    assert text == "I have worked with GraphQL."


@pytest.mark.asyncio
async def test_receive_candidate_text_merges_partial_text_fragments(monkeypatch):
    monkeypatch.setattr(websocket_handler, "_TEXT_CONTINUATION_WINDOW_SECONDS", 0.001)
    ws = StubWebSocket(
        messages=[
            "{\"type\":\"text\",\"text\":\"I am a senior software engineer\"}",
            "{\"type\":\"text\",\"text\":\"I am a senior software engineer with over 9 years of experience.\"}",
        ]
    )

    text = await websocket_handler._receive_candidate_text(
        websocket=ws,
        timeout=0.02,
        retries=0,
        add_segment=lambda *_: None,
        nudge="Please continue when ready.",
    )

    assert text == "I am a senior software engineer with over 9 years of experience."


@pytest.mark.asyncio
async def test_receive_candidate_text_uses_latest_nudge_as_echo_reference(monkeypatch):
    monkeypatch.setattr(websocket_handler, "_TEXT_CONTINUATION_WINDOW_SECONDS", 0.001)

    class DelayedThenMessagesWebSocket:
        def __init__(self):
            self.sent = []
            self.calls = 0

        async def receive_text(self):
            self.calls += 1
            if self.calls == 1:
                await asyncio.sleep(0.02)
                return ""
            if self.calls == 2:
                return "{\"type\":\"text\",\"text\":\"I'm here when you're ready. Take your time.\"}"
            if self.calls == 3:
                return "{\"type\":\"text\",\"text\":\"I have over nine years of backend experience.\"}"
            await asyncio.sleep(0)
            return ""

        async def send_json(self, payload):
            self.sent.append(payload)

    ws = DelayedThenMessagesWebSocket()
    segments = []
    nudge = "I'm here when you're ready. Take your time."

    text = await websocket_handler._receive_candidate_text(
        websocket=ws,
        timeout=0.01,
        retries=1,
        add_segment=lambda speaker, value: segments.append((speaker, value)),
        nudge=nudge,
        last_emma_text="Hello! I'm Emma. I'll ask you a few questions about your experience.",
    )

    assert text == "I have over nine years of backend experience."
    assert segments == [("emma", nudge)]


def test_is_role_question_requires_role_context():
    assert websocket_handler._is_role_question("How does the role handle on-call?") is True
    assert websocket_handler._is_role_question("I was trying to answer your previous question") is False
    assert websocket_handler._is_role_question("What do you mean?") is False


def test_sanitize_text_removes_null_and_control_chars():
    raw = "Hi\x00 there\x01 this is\x02 clean"
    assert websocket_handler._sanitize_text(raw) == "Hi there this is clean"


@pytest.mark.asyncio
async def test_receive_candidate_text_drops_binary_audio_without_stt_and_returns_none():
    payload = base64.b64encode(b"\x00\x11\x22\x33\x44\x55").decode("ascii")
    ws = StubWebSocket(
        messages=[
            '{"type":"audio_start","codec":"webm-opus","sample_rate_hz":48000}',
            f'{{"type":"audio_chunk","data_b64":"{payload}","seq":0,"is_final":true}}',
        ],
        block_forever=True,
    )

    async def fake_binary_transcriber(chunks, codec, sample_rate_hz):
        return "\x00\x00\x11\x22"

    text = await websocket_handler._receive_candidate_text(
        websocket=ws,
        timeout=0.01,
        retries=0,
        add_segment=lambda *_: None,
        nudge="Please continue when ready.",
        transcribe_audio=fake_binary_transcriber,
    )

    assert text is None


@pytest.mark.asyncio
async def test_handle_call_websocket_rejects_duplicate_with_4409():
    ws = StubWebSocket()
    ws.closed = None

    class DuplicateCallService:
        def is_application_in_call(self, _):
            return True

    class DummyEmma:
        pass

    await websocket_handler.handle_call_websocket(
        websocket=ws,
        application_id_str="00000000-0000-0000-0000-000000000111",
        get_call_service=lambda: DuplicateCallService(),
        get_emma_service=lambda: DummyEmma(),
    )

    assert ws.closed == {
        "code": 4409,
        "reason": "Call already active for this application",
    }
