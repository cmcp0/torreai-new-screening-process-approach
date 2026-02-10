import asyncio
import logging
from typing import TYPE_CHECKING

from src.screening.calls.domain.events import CallFinished

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

_ANALYSIS_RETRIES = 3
_ANALYSIS_BACKOFF_BASE = 1.0

# Analysis runs asynchronously (run_analysis is async). When CallFinished is published
# from an async context (e.g. WebSocket close), we schedule run_analysis via create_task
# so the event loop is not blocked. When consumed from sync threads (e.g. RabbitMQ),
# we run analysis in a dedicated event loop for that thread.


async def _run_analysis_with_retry(application_id, call_id) -> None:
    from src.wiring import get_analysis_service
    service = get_analysis_service()
    last_error = None
    for attempt in range(_ANALYSIS_RETRIES):
        try:
            await service.run_analysis(application_id, call_id)
            return
        except Exception as e:
            last_error = e
            logger.warning("Analysis attempt %s failed: %s", attempt + 1, e)
            if attempt < _ANALYSIS_RETRIES - 1:
                await asyncio.sleep(_ANALYSIS_BACKOFF_BASE * (2 ** attempt))
    logger.exception("Analysis failed after %s attempts; persisting failed state", _ANALYSIS_RETRIES)
    try:
        await service.persist_analysis_failed(application_id)
    except Exception as e:
        logger.exception("Could not persist analysis failed state: %s", e)


def on_call_finished(event: CallFinished) -> None:
    try:
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_run_analysis_with_retry(event.application_id, event.call_id))
        except RuntimeError:
            logger.info(
                "No running event loop; running analysis in sync thread for application %s",
                event.application_id,
            )
            asyncio.run(_run_analysis_with_retry(event.application_id, event.call_id))
    except Exception as e:
        logger.exception("Analysis subscriber failed: %s", e)
