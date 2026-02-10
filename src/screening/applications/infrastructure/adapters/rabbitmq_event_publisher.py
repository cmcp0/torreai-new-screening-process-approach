import logging
import threading
from typing import Callable

import pika
from pika.exceptions import AMQPConnectionError, AMQPChannelError

from src.screening.applications.domain.ports import EventPublisher, EventPublishError
from src.screening.applications.infrastructure.adapters.event_codec import (
    deserialize_event,
    serialize_event,
)
from src.shared.domain.events import DomainEvent

logger = logging.getLogger(__name__)

QUEUE_NAME = "screening.events"


class BrokerUnavailableError(EventPublishError):
    """Raised when publish fails due to broker connection or channel error."""


class RabbitMQEventPublisher(EventPublisher):
    def __init__(self, broker_url: str) -> None:
        self._broker_url = broker_url
        self._handlers: list[Callable[[DomainEvent], None]] = []
        self._consumer_thread: threading.Thread | None = None
        self._consumer_stop = threading.Event()

    def subscribe(self, handler: Callable[[DomainEvent], None]) -> None:
        self._handlers.append(handler)

    def publish(self, event: DomainEvent) -> None:
        body = serialize_event(event)
        try:
            params = pika.URLParameters(self._broker_url)
            conn = pika.BlockingConnection(params)
            ch = conn.channel()
            ch.queue_declare(queue=QUEUE_NAME, durable=True)
            ch.basic_publish(
                exchange="",
                routing_key=QUEUE_NAME,
                body=body,
                properties=pika.BasicProperties(delivery_mode=2),
            )
            conn.close()
        except (AMQPConnectionError, AMQPChannelError, OSError) as e:
            logger.exception("RabbitMQ publish failed: %s", e)
            raise BrokerUnavailableError("Broker unavailable") from e

    def _dispatch(self, event: DomainEvent) -> None:
        errors: list[Exception] = []
        for handler in self._handlers:
            try:
                handler(event)
            except Exception as e:
                logger.exception("Event handler failed: %s", e)
                errors.append(e)
        if errors:
            raise RuntimeError(f"{len(errors)} event handler(s) failed")

    def _consume_loop(self) -> None:
        while not self._consumer_stop.is_set():
            try:
                params = pika.URLParameters(self._broker_url)
                conn = pika.BlockingConnection(params)
                ch = conn.channel()
                ch.queue_declare(queue=QUEUE_NAME, durable=True)
                ch.basic_qos(prefetch_count=1)

                def on_message(channel, method, properties, body):
                    try:
                        event = deserialize_event(body)
                        self._dispatch(event)
                        channel.basic_ack(delivery_tag=method.delivery_tag)
                    except Exception as e:
                        logger.exception("Consumer handler failed: %s", e)
                        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

                ch.basic_consume(queue=QUEUE_NAME, on_message_callback=on_message)
                while not self._consumer_stop.is_set():
                    conn.process_data_events(time_limit=1)
                conn.close()
            except (AMQPConnectionError, AMQPChannelError, OSError) as e:
                if self._consumer_stop.is_set():
                    break
                logger.warning("Consumer connection error, reconnecting: %s", e)
                self._consumer_stop.wait(5)

    def start_consumer(self) -> None:
        if self._consumer_thread is not None:
            return
        self._consumer_stop.clear()
        self._consumer_thread = threading.Thread(target=self._consume_loop, daemon=True)
        self._consumer_thread.start()
        logger.info("RabbitMQ consumer started for queue %s", QUEUE_NAME)
