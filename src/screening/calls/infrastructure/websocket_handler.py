import asyncio
import base64
from difflib import SequenceMatcher
import json
import logging
import time
from typing import Awaitable, Callable, Optional, TYPE_CHECKING

from fastapi import WebSocket, WebSocketDisconnect

from src.screening.shared.domain import ApplicationId
from src.screening.calls.domain.entities import TranscriptSegment

if TYPE_CHECKING:
    from src.config import Settings
    from src.screening.calls.application.services import CallService, EmmaService

logger = logging.getLogger(__name__)


_DUPLICATE_CALL_CLOSE_CODE = 4409
_DEFAULT_READY_TIMEOUT_BASE_SECONDS = 5.0
_DEFAULT_READY_TIMEOUT_MAX_SECONDS = 20.0
_DEFAULT_ANSWER_TIMEOUT_SECONDS = 45.0
_DEFAULT_SILENCE_RETRIES = 2
_TEXT_CONTINUATION_WINDOW_SECONDS = 2.2

AudioTranscriber = Callable[[list[bytes], str, int], Awaitable[str]]


async def handle_call_websocket(
    websocket: WebSocket,
    application_id_str: str,
    get_call_service: Callable[[], "CallService"],
    get_emma_service: Callable[[], "EmmaService"],
    get_settings: Optional[Callable[[], "Settings"]] = None,
    get_audio_transcriber: Optional[Callable[[], AudioTranscriber]] = None,
) -> None:
    try:
        application_id = ApplicationId(application_id_str)
    except (ValueError, TypeError):
        await websocket.close(code=4000, reason="Invalid application_id")
        return

    settings = get_settings() if get_settings else None
    ready_timeout_base = float(
        getattr(settings, "ready_timeout_base_seconds", _DEFAULT_READY_TIMEOUT_BASE_SECONDS)
    )
    ready_timeout_max = float(
        getattr(settings, "ready_timeout_max_seconds", _DEFAULT_READY_TIMEOUT_MAX_SECONDS)
    )
    answer_timeout = float(
        getattr(settings, "answer_timeout_seconds", _DEFAULT_ANSWER_TIMEOUT_SECONDS)
    )
    silence_retries = int(getattr(settings, "silence_retries", _DEFAULT_SILENCE_RETRIES))

    audio_transcriber = get_audio_transcriber() if get_audio_transcriber else _transcribe_audio_stub

    call_service = get_call_service()
    if call_service.is_application_in_call(application_id):
        await websocket.close(
            code=_DUPLICATE_CALL_CLOSE_CODE,
            reason="Call already active for this application",
        )
        return

    call = call_service.start_call(application_id)
    transcript: list[TranscriptSegment] = []
    start_time = time.monotonic()

    def add_segment(speaker: str, text: str) -> None:
        cleaned = _sanitize_text(text)
        if not cleaned:
            return
        ts = time.monotonic() - start_time
        transcript.append(TranscriptSegment(speaker=speaker, text=cleaned, timestamp=ts))

    try:
        await websocket.accept()

        prompt = call_service.get_prompt_for_application(application_id)
        emma = get_emma_service()

        greeting = await emma.greeting(prompt.role_context)
        add_segment("emma", greeting)
        await _send_emma_turn(websocket, greeting)

        initial_text = await _receive_candidate_text(
            websocket=websocket,
            timeout=ready_timeout_base,
            adaptive_max_timeout=ready_timeout_max,
            retries=silence_retries,
            add_segment=add_segment,
            nudge="I'm here when you're ready. Take your time.",
            last_emma_text=greeting,
            transcribe_audio=audio_transcriber,
        )
        if initial_text:
            add_segment("candidate", initial_text)
            await _send_text(websocket, initial_text, speaker="candidate")

        question_index = 0
        while question_index < len(prompt.prepared_questions):
            question = await emma.next_question(
                question_index, prompt.prepared_questions, prompt.role_context
            )
            if question is None:
                break
            add_segment("emma", question)
            await _send_emma_turn(websocket, question)

            candidate_text = await _receive_candidate_text(
                websocket=websocket,
                timeout=answer_timeout,
                retries=silence_retries,
                add_segment=add_segment,
                nudge="I'm still listening. Feel free to answer when you're ready.",
                last_emma_text=question,
                transcribe_audio=audio_transcriber,
            )

            if candidate_text:
                add_segment("candidate", candidate_text)
                await _send_text(websocket, candidate_text, speaker="candidate")
            else:
                add_segment("candidate", "[no response]")
                # Stop advancing if we never got a candidate response to avoid spilling all questions.
                break

            if _is_role_question(candidate_text):
                role_answer = await emma.answer_role_question(
                    candidate_text, prompt.role_context
                )
                add_segment("emma", role_answer)
                await _send_emma_turn(websocket, role_answer)

            question_index += 1

        goodbye = await emma.goodbye()
        add_segment("emma", goodbye)
        await _send_emma_turn(websocket, goodbye, end_with_listening=False)
        await _send_control(websocket, "call_ended")
    except WebSocketDisconnect:
        pass
    finally:
        try:
            await asyncio.to_thread(
                call_service.end_call,
                application_id,
                call.id,
                transcript,
            )
        except Exception as exc:
            logger.exception("Failed to finalize call %s: %s", call.id, exc)


async def _receive_candidate_text(
    websocket: WebSocket,
    timeout: float,
    retries: int,
    add_segment: Callable[[str, str], None],
    nudge: str,
    last_emma_text: Optional[str] = None,
    adaptive_max_timeout: Optional[float] = None,
    transcribe_audio: Optional[AudioTranscriber] = None,
) -> Optional[str]:
    transcriber = transcribe_audio or _transcribe_audio_stub
    active_last_emma_text = last_emma_text

    attempt = 0
    while attempt <= retries:
        attempt_start = time.monotonic()
        max_timeout = adaptive_max_timeout if adaptive_max_timeout is not None else timeout
        max_deadline = attempt_start + max(timeout, max_timeout)
        deadline = attempt_start + timeout

        audio_session: Optional[dict[str, object]] = None
        pending_text: Optional[str] = None
        pending_text_deadline: Optional[float] = None

        while True:
            now = time.monotonic()
            active_deadline = pending_text_deadline if pending_text_deadline is not None else deadline
            remaining = active_deadline - now
            if remaining <= 0:
                if pending_text:
                    return pending_text
                break
            try:
                raw_msg = await asyncio.wait_for(websocket.receive_text(), timeout=remaining)
            except asyncio.TimeoutError:
                if pending_text:
                    return pending_text
                break

            parsed = _parse_client_message(raw_msg)

            if isinstance(parsed, dict):
                msg_type = str(parsed.get("type", "")).strip().lower()

                if msg_type == "text":
                    candidate_text = _sanitize_text(str(parsed.get("text") or ""))
                    if not candidate_text:
                        continue
                    if _is_echo_of_emma(candidate_text, active_last_emma_text):
                        logger.info("Ignoring likely echo of Emma speech from client transcription.")
                        continue
                    pending_text = _merge_candidate_text_fragments(pending_text, candidate_text)
                    pending_text_deadline = time.monotonic() + _TEXT_CONTINUATION_WINDOW_SECONDS
                    continue

                if msg_type == "audio_start":
                    audio_session = {
                        "codec": str(parsed.get("codec") or "webm-opus"),
                        "sample_rate_hz": int(parsed.get("sample_rate_hz") or 16000),
                        "chunks": [],
                    }
                    deadline = max_deadline
                    continue

                if msg_type == "audio_chunk":
                    if audio_session is None:
                        audio_session = {
                            "codec": "webm-opus",
                            "sample_rate_hz": 16000,
                            "chunks": [],
                        }
                    decoded = _decode_audio_chunk(str(parsed.get("data_b64") or ""))
                    if decoded:
                        chunks = audio_session["chunks"]
                        if isinstance(chunks, list):
                            chunks.append(decoded)
                    deadline = max_deadline
                    if bool(parsed.get("is_final")):
                        candidate_text = await _finalize_audio_session(
                            audio_session,
                            transcriber,
                        )
                        if candidate_text and not _is_echo_of_emma(candidate_text, active_last_emma_text):
                            return candidate_text
                        audio_session = None
                    continue

                if msg_type == "audio_end":
                    if audio_session is None:
                        continue
                    candidate_text = await _finalize_audio_session(
                        audio_session,
                        transcriber,
                    )
                    if candidate_text and not _is_echo_of_emma(candidate_text, active_last_emma_text):
                        return candidate_text
                    audio_session = None
                    continue

                continue

            candidate_text = raw_msg.strip() if isinstance(raw_msg, str) else ""
            candidate_text = _sanitize_text(candidate_text)
            if not candidate_text:
                continue
            if _is_echo_of_emma(candidate_text, active_last_emma_text):
                logger.info("Ignoring likely echo of Emma speech from client transcription.")
                continue
            pending_text = _merge_candidate_text_fragments(pending_text, candidate_text)
            pending_text_deadline = time.monotonic() + _TEXT_CONTINUATION_WINDOW_SECONDS

        if attempt >= retries:
            return None

        add_segment("emma", nudge)
        await _send_emma_turn(websocket, nudge)
        active_last_emma_text = nudge
        attempt += 1

    return None


def _parse_client_message(msg: str):
    try:
        return json.loads(msg)
    except json.JSONDecodeError:
        return None


def _decode_audio_chunk(data_b64: str) -> bytes:
    if not data_b64:
        return b""
    try:
        return base64.b64decode(data_b64, validate=False)
    except Exception:
        return b""


async def _finalize_audio_session(
    audio_session: dict[str, object],
    transcriber: AudioTranscriber,
) -> str:
    codec = str(audio_session.get("codec") or "webm-opus")
    sample_rate_hz = int(audio_session.get("sample_rate_hz") or 16000)
    chunks = audio_session.get("chunks")
    if not isinstance(chunks, list):
        return ""
    byte_chunks = [c for c in chunks if isinstance(c, (bytes, bytearray))]
    if not byte_chunks:
        return ""
    try:
        out = await transcriber([bytes(c) for c in byte_chunks], codec, sample_rate_hz)
        cleaned = _sanitize_text(out) if isinstance(out, str) else ""
        return cleaned if _looks_like_human_candidate_text(cleaned) else ""
    except Exception as exc:
        logger.warning("Audio transcription failed: %s", exc)
        return ""


def _normalize_for_similarity(text: str) -> str:
    return " ".join(
        "".join(ch.lower() if ch.isalnum() else " " for ch in text).split()
    )


def _sanitize_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    cleaned = "".join(ch for ch in text if ch == "\n" or ch == "\t" or ord(ch) >= 32)
    cleaned = cleaned.replace("\u2028", " ").replace("\u2029", " ")
    cleaned = " ".join(cleaned.split())
    return cleaned.strip()


def _merge_candidate_text_fragments(existing: Optional[str], incoming: str) -> str:
    if not existing:
        return incoming
    if not incoming:
        return existing

    left = _sanitize_text(existing)
    right = _sanitize_text(incoming)
    if not left:
        return right
    if not right:
        return left

    if right.startswith(left):
        return right
    if left.startswith(right):
        return left

    max_overlap = min(len(left), len(right))
    for size in range(max_overlap, 0, -1):
        if left[-size:].lower() == right[:size].lower():
            return _sanitize_text(left + right[size:])

    return _sanitize_text(f"{left} {right}")


def _looks_like_human_candidate_text(text: str) -> bool:
    if not text:
        return False
    if len(text) < 2:
        return False
    alnum_count = sum(1 for ch in text if ch.isalnum())
    if alnum_count == 0:
        return False
    return (alnum_count / len(text)) >= 0.25


def _is_echo_of_emma(candidate_text: str, last_emma_text: Optional[str]) -> bool:
    if not candidate_text or not last_emma_text:
        return False
    candidate = _normalize_for_similarity(candidate_text)
    emma = _normalize_for_similarity(last_emma_text)
    if not candidate or not emma:
        return False
    if candidate == emma:
        return True
    similarity = SequenceMatcher(None, candidate, emma).ratio()
    if similarity >= 0.82:
        return True
    if len(candidate) >= 30 and len(emma) >= 30:
        shorter, longer = (candidate, emma) if len(candidate) <= len(emma) else (emma, candidate)
        if shorter in longer and (len(shorter) / len(longer)) >= 0.88:
            return True
    return False


def _is_role_question(text: str) -> bool:
    if not text or len(text) < 3:
        return False

    lower = text.lower().strip()

    role_keywords = (
        "role",
        "job",
        "responsibilit",
        "team",
        "stack",
        "expectation",
        "position",
        "company",
    )
    if not any(k in lower for k in role_keywords):
        return False

    if "?" in lower:
        return True

    question_starters = (
        "what ",
        "how ",
        "why ",
        "when ",
        "where ",
        "which ",
        "can you ",
        "could you ",
        "would you ",
        "is the ",
        "are the ",
    )
    return lower.startswith(question_starters)


async def _send_control(websocket: WebSocket, event: str) -> None:
    await websocket.send_json({"type": "control", "event": event})


async def _send_text(websocket: WebSocket, text: str, speaker: str = "emma") -> None:
    await websocket.send_json({"type": "text", "text": text, "speaker": speaker})


async def _send_audio_chunk(
    websocket: WebSocket,
    speaker: str,
    codec: str,
    seq: int,
    data: bytes,
    is_final: bool,
) -> None:
    await websocket.send_json(
        {
            "type": "audio_chunk",
            "speaker": speaker,
            "codec": codec,
            "seq": seq,
            "data_b64": base64.b64encode(data).decode("ascii"),
            "is_final": is_final,
        }
    )


async def _send_emma_turn(
    websocket: WebSocket,
    text: str,
    end_with_listening: bool = True,
    audio_chunks: Optional[list[bytes]] = None,
    codec: str = "webm-opus",
) -> None:
    await _send_control(websocket, "emma_speaking")
    await _send_text(websocket, text)

    if audio_chunks:
        last_idx = len(audio_chunks) - 1
        for idx, chunk in enumerate(audio_chunks):
            await _send_audio_chunk(
                websocket=websocket,
                speaker="emma",
                codec=codec,
                seq=idx,
                data=chunk,
                is_final=idx == last_idx,
            )

    if end_with_listening:
        await _send_control(websocket, "listening")


async def _transcribe_audio_stub(chunks: list[bytes], codec: str, sample_rate_hz: int) -> str:
    return ""
