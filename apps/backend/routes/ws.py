import inspect

from fastapi import APIRouter, Query, WebSocket

from src import wiring
from src.screening.calls.infrastructure.websocket_handler import (
    handle_call_websocket,
)

router = APIRouter(tags=["ws"])


@router.websocket("/ws/call")
async def ws_call(
    websocket: WebSocket,
    application_id: str = Query(..., alias="application_id"),
) -> None:
    handler_params = inspect.signature(handle_call_websocket).parameters
    kwargs = dict(
        websocket=websocket,
        application_id_str=application_id,
        get_call_service=wiring.get_call_service,
        get_emma_service=wiring.get_emma_service,
    )

    if "get_settings" in handler_params and hasattr(wiring, "get_settings"):
        kwargs["get_settings"] = wiring.get_settings

    audio_transcriber_factory = getattr(wiring, "get_audio_transcriber", None)
    if "get_audio_transcriber" in handler_params and callable(audio_transcriber_factory):
        kwargs["get_audio_transcriber"] = audio_transcriber_factory

    await handle_call_websocket(**kwargs)
