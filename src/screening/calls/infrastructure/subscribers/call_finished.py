import asyncio
import logging
from typing import TYPE_CHECKING

from src.screening.calls.domain.events import CallFinished

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Analysis runs asynchronously (run_analysis is async). When CallFinished is published
# from an async context (e.g. WebSocket close), we schedule run_analysis via create_task
# so the event loop is not blocked. If no running loop (e.g. sync tests), analysis is skipped.


def on_call_finished(event: CallFinished) -> None:
    try:
        from src.wiring import get_analysis_service
        from src.screening.analysis.application.services import AnalysisService
        service = get_analysis_service()
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(service.run_analysis(event.application_id, event.call_id))
        except RuntimeError:
            logger.warning("No running event loop; analysis skipped for application %s", event.application_id)
    except Exception as e:
        logger.exception("Analysis subscriber failed: %s", e)
