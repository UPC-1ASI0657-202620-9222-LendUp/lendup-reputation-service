from __future__ import annotations

import logging
import time
from collections.abc import Callable
from threading import Event
from typing import Any, Protocol

import pika
from pika.exceptions import AMQPError
from pika.exchange_type import ExchangeType
from pydantic import ValidationError

from lendup_reputation.config.settings import Settings
from lendup_reputation.infrastructure.messaging.contracts import PrestamoFinalizadoV1


class LoanEventProcessor(Protocol):
    def process(self, event: PrestamoFinalizadoV1) -> bool: ...


class RabbitMqLoanConsumer:
    """Owns RabbitMQ connection, topology, delivery settlement, retry and reconnection."""

    def __init__(
        self,
        settings: Settings,
        processor: LoanEventProcessor,
        *,
        connection_factory: Callable[[pika.URLParameters], Any] = pika.BlockingConnection,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self._settings = settings
        self._processor = processor
        self._connection_factory = connection_factory
        self._sleeper = sleeper
        self._stopping = Event()
        self._connection: Any | None = None
        self._channel: Any | None = None
        self._logger = logging.getLogger(__name__)

    @property
    def retry_queue(self) -> str:
        return self._settings.rabbitmq_retry_queue or (
            f"{self._settings.rabbitmq_loan_queue}.retry"
        )

    def run_forever(self) -> None:
        delay = 1.0
        while not self._stopping.is_set():
            try:
                self._consume_once()
                delay = 1.0
            except (AMQPError, OSError) as exc:
                if self._stopping.is_set():
                    break
                self._logger.warning("rabbitmq_consumer_disconnected", exc_info=exc)
                self._sleeper(delay)
                delay = min(delay * 2, self._settings.consumer_reconnect_max_seconds)

    def stop(self) -> None:
        self._stopping.set()
        connection = self._connection
        if connection is not None and connection.is_open:
            connection.add_callback_threadsafe(self._stop_consuming)

    def _stop_consuming(self) -> None:
        channel = self._channel
        if channel is not None and channel.is_open:
            channel.stop_consuming()

    def _consume_once(self) -> None:
        parameters = pika.URLParameters(self._settings.rabbitmq_url.get_secret_value())
        connection = self._connection_factory(parameters)
        self._connection = connection
        try:
            channel = connection.channel()
            self._channel = channel
            self._configure_channel(channel)
            channel.basic_consume(
                queue=self._settings.rabbitmq_loan_queue or "",
                on_message_callback=self.handle_delivery,
                auto_ack=False,
            )
            channel.start_consuming()
        finally:
            if connection.is_open:
                connection.close()
            self._channel = None
            self._connection = None

    def _configure_channel(self, channel: Any) -> None:
        exchange = self._settings.rabbitmq_exchange or ""
        queue = self._settings.rabbitmq_loan_queue or ""
        routing_key = self._settings.rabbitmq_loan_routing_key or ""
        dlq = self._settings.rabbitmq_dlq or ""
        channel.exchange_declare(exchange=exchange, exchange_type=ExchangeType.topic, durable=True)
        channel.queue_declare(queue=dlq, durable=True)
        channel.queue_declare(
            queue=queue,
            durable=True,
            arguments={"x-dead-letter-exchange": "", "x-dead-letter-routing-key": dlq},
        )
        channel.queue_bind(queue=queue, exchange=exchange, routing_key=routing_key)
        channel.queue_declare(
            queue=self.retry_queue,
            durable=True,
            arguments={
                "x-dead-letter-exchange": exchange,
                "x-dead-letter-routing-key": routing_key,
            },
        )
        channel.basic_qos(prefetch_count=1)

    def handle_delivery(
        self, channel: Any, method: Any, properties: pika.BasicProperties, body: bytes
    ) -> None:
        correlation_id = properties.correlation_id
        try:
            event = PrestamoFinalizadoV1.model_validate_json(body)
        except (ValidationError, ValueError):
            self._logger.warning(
                "invalid_loan_event",
                extra={"correlation_id": correlation_id},
                exc_info=True,
            )
            channel.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
            return
        try:
            self._processor.process(event)
        except Exception:
            self._logger.exception(
                "loan_event_processing_failed",
                extra={"correlation_id": str(event.correlation_id)},
            )
            self._retry_or_dead_letter(channel, method, properties, body, event)
            return
        channel.basic_ack(delivery_tag=method.delivery_tag)

    def _retry_or_dead_letter(
        self,
        channel: Any,
        method: Any,
        properties: pika.BasicProperties,
        body: bytes,
        event: PrestamoFinalizadoV1,
    ) -> None:
        headers = dict(properties.headers or {})
        attempts = int(headers.get("x-lendup-retry", 0))
        if attempts >= self._settings.consumer_max_retries:
            channel.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
            return
        headers["x-lendup-retry"] = attempts + 1
        delay_ms = min(
            self._settings.consumer_retry_max_ms,
            self._settings.consumer_retry_base_ms * (2**attempts),
        )
        channel.confirm_delivery()
        channel.basic_publish(
            exchange="",
            routing_key=self.retry_queue,
            body=body,
            properties=pika.BasicProperties(
                content_type=properties.content_type or "application/json",
                delivery_mode=2,
                message_id=properties.message_id or str(event.event_id),
                correlation_id=properties.correlation_id or str(event.correlation_id),
                headers=headers,
                expiration=str(delay_ms),
            ),
            mandatory=True,
        )
        channel.basic_ack(delivery_tag=method.delivery_tag)
