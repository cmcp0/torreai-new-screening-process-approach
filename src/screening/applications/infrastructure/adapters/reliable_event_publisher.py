import logging
import threading
from typing import Callable

from src.screening.applications.domain.ports import EventPublisher
from src.screening.applications.infrastructure.adapters.event_codec import (
    envelope_to_event,
    event_to_envelope,
)
from src.screening.applications.infrastructure.adapters.outbox_repository import (
    OutboxRepository,
)
from src.shared.domain.events import DomainEvent

logger = logging.getLogger(__name__)


class ReliableEventPublisher(EventPublisher):
    """
    Outbox-backed publisher.

    - Persist event in outbox first.
    - Try immediate publish.
    - Keep pending rows for relay retries (at-least-once delivery).
    """

    def __init__(
        self,
        delegate: EventPublisher,
        outbox_repository: OutboxRepository,
        flush_interval_seconds: float = 2.0,
    ) -> None:
        self._delegate = delegate
        self._outbox = outbox_repository
        self._flush_interval_seconds = max(0.2, float(flush_interval_seconds))
        self._drain_lock = threading.Lock()
        self._relay_stop = threading.Event()
        self._relay_thread: threading.Thread | None = None

    def subscribe(self, handler: Callable[[DomainEvent], None]) -> None:
        subscribe = getattr(self._delegate, "subscribe", None)
        if callable(subscribe):
            subscribe(handler)
            return
        raise AttributeError("Delegate publisher does not support subscribe")

    def publish(self, event: DomainEvent) -> None:
        envelope = event_to_envelope(event)
        event_type = str(envelope.get("type", type(event).__name__))
        outbox_id = self._outbox.save_pending(event_type=event_type, payload=envelope)

        try:
            self._delegate.publish(event)
        except Exception as exc:
            self._outbox.mark_failed_attempt(outbox_id, str(exc))
            raise

        self._outbox.mark_published(outbox_id)
        self._drain_pending_once(limit=100)

    def start_relay(self) -> None:
        if self._relay_thread is not None and self._relay_thread.is_alive():
            return
        self._relay_stop.clear()
        self._relay_thread = threading.Thread(
            target=self._relay_loop,
            daemon=True,
            name="event_outbox_relay",
        )
        self._relay_thread.start()
        logger.info("Reliable outbox relay started")

    def _relay_loop(self) -> None:
        while not self._relay_stop.is_set():
            try:
                self._drain_pending_once(limit=100)
            except Exception as exc:
                logger.warning("Outbox relay loop failed: %s", exc)
            self._relay_stop.wait(self._flush_interval_seconds)

    def _drain_pending_once(self, limit: int = 100) -> None:
        if not self._drain_lock.acquire(blocking=False):
            return
        try:
            pending = self._outbox.list_pending(limit=limit)
            for row in pending:
                try:
                    event = envelope_to_event(row.payload)
                    self._delegate.publish(event)
                    self._outbox.mark_published(row.id)
                except Exception as exc:
                    self._outbox.mark_failed_attempt(row.id, str(exc))
                    logger.warning(
                        "Outbox replay failed for %s (%s): %s",
                        row.id,
                        row.event_type,
                        exc,
                    )
                    # Stop this drain pass to avoid hot-looping against a down broker.
                    break
        finally:
            self._drain_lock.release()
