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
    await handle_call_websocket(
        websocket=websocket,
        application_id_str=application_id,
        get_call_service=wiring.get_call_service,
        get_emma_service=wiring.get_emma_service,
    )
