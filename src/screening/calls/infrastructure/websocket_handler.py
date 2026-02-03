import asyncio
import json
import logging
import time
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from src.screening.shared.domain import ApplicationId
from src.screening.calls.domain.entities import TranscriptSegment

logger = logging.getLogger(__name__)


async def handle_call_websocket(
    websocket: WebSocket,
    application_id_str: str,
    get_call_service: callable,
    get_emma_service: callable,
) -> None:
    try:
        application_id = ApplicationId(application_id_str)
    except (ValueError, TypeError):
        await websocket.close(code=4000, reason="Invalid application_id")
        return

    call_service = get_call_service()
    if call_service.is_application_in_call(application_id):
        await websocket.close(code=409, reason="Call already active for this application")
        return

    call = call_service.start_call(application_id)
    transcript: list[TranscriptSegment] = []
    start_time = time.monotonic()

    def add_segment(speaker: str, text: str) -> None:
        ts = time.monotonic() - start_time
        transcript.append(TranscriptSegment(speaker=speaker, text=text, timestamp=ts))

    try:
        await websocket.accept()
        await _send_control(websocket, "listening")

        prompt = call_service.get_prompt_for_application(application_id)
        emma = get_emma_service()

        greeting = await emma.greeting(prompt.role_context)
        add_segment("emma", greeting)
        await _send_control(websocket, "emma_speaking")
        await _send_text(websocket, greeting)
        await _send_control(websocket, "listening")

        try:
            await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
        except asyncio.TimeoutError:
            pass

        question_index = 0
        while question_index < len(prompt.prepared_questions):
            question = await emma.next_question(
                question_index, prompt.prepared_questions, prompt.role_context
            )
            if question is None:
                break
            add_segment("emma", question)
            await _send_control(websocket, "emma_speaking")
            await _send_text(websocket, question)
            await _send_control(websocket, "listening")

            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                add_segment("candidate", "[no response]")
                question_index += 1
                continue

            candidate_text = _extract_candidate_text(msg)
            add_segment("candidate", candidate_text)

            if _is_role_question(candidate_text):
                role_answer = await emma.answer_role_question(
                    candidate_text, prompt.role_context
                )
                add_segment("emma", role_answer)
                await _send_control(websocket, "emma_speaking")
                await _send_text(websocket, role_answer)
                await _send_control(websocket, "listening")

            question_index += 1

        goodbye = await emma.goodbye()
        add_segment("emma", goodbye)
        await _send_control(websocket, "emma_speaking")
        await _send_text(websocket, goodbye)
        await _send_control(websocket, "call_ended")
    except WebSocketDisconnect:
        pass
    finally:
        call_service.end_call(application_id, call.id, transcript)


def _parse_client_message(msg: str):
    try:
        return json.loads(msg)
    except json.JSONDecodeError:
        return None


def _extract_candidate_text(msg: str) -> str:
    data = _parse_client_message(msg)
    if data and data.get("type") == "text" and data.get("text"):
        return data["text"]
    return msg.strip() if isinstance(msg, str) and msg.strip() else ""


def _is_role_question(text: str) -> bool:
    if not text or len(text) < 3:
        return False
    lower = text.lower().strip()
    role_keywords = ("what", "how", "role", "job", "responsibilit", "require", "?")
    return any(k in lower for k in role_keywords)


async def _send_control(websocket: WebSocket, event: str) -> None:
    await websocket.send_json({"type": "control", "event": event})


async def _send_text(websocket: WebSocket, text: str) -> None:
    await websocket.send_json({"type": "text", "text": text})
