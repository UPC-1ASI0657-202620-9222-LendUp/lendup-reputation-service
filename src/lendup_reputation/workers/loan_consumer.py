from __future__ import annotations

import json
import logging
import signal
from typing import Any

import pika
from pika.exchange_type import ExchangeType
from pydantic import ValidationError

from lendup_reputation.config.logging import configure_logging
from lendup_reputation.config.settings import get_settings
from lendup_reputation.infrastructure.messaging.contracts import PrestamoFinalizadoV1
from lendup_reputation.infrastructure.messaging.inbox import LoanProjectionConsumer
from lendup_reputation.infrastructure.persistence.database import (
    create_database_engine,
    create_session_factory,
)


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = logging.getLogger(__name__)
    if not settings.loan_subscription_enabled:
        raise RuntimeError("LOAN_SUBSCRIPTION_ENABLED debe ser true para iniciar este worker")
    settings.validate_worker_configuration("consumer")
    engine = create_database_engine(settings)
    processor = LoanProjectionConsumer(create_session_factory(engine))
    parameters = pika.URLParameters(settings.rabbitmq_url.get_secret_value())
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    channel.exchange_declare(
        exchange=settings.rabbitmq_exchange or "", exchange_type=ExchangeType.topic, durable=True
    )
    channel.queue_declare(queue=settings.rabbitmq_dlq or "", durable=True)
    channel.queue_declare(
        queue=settings.rabbitmq_loan_queue or "",
        durable=True,
        arguments={
            "x-dead-letter-exchange": "",
            "x-dead-letter-routing-key": settings.rabbitmq_dlq,
        },
    )
    channel.queue_bind(
        queue=settings.rabbitmq_loan_queue or "",
        exchange=settings.rabbitmq_exchange or "",
        routing_key=settings.rabbitmq_loan_routing_key or "",
    )
    retry_queue = f"{settings.rabbitmq_loan_queue}.retry"
    channel.queue_declare(
        queue=retry_queue,
        durable=True,
        arguments={
            "x-dead-letter-exchange": settings.rabbitmq_exchange,
            "x-dead-letter-routing-key": settings.rabbitmq_loan_routing_key,
        },
    )
    channel.basic_qos(prefetch_count=1)

    def callback(ch: Any, method: Any, properties: pika.BasicProperties, body: bytes) -> None:
        try:
            raw = json.loads(body)
            event = PrestamoFinalizadoV1.model_validate(raw)
        except (json.JSONDecodeError, UnicodeDecodeError, ValidationError):
            logger.exception("invalid_loan_event")
            ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
            return
        try:
            processor.process(event)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception:
            logger.exception("loan_event_processing_failed")
            headers = dict(properties.headers or {})
            attempts = int(headers.get("x-lendup-retry", 0))
            if attempts >= 5:
                ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
                return
            headers["x-lendup-retry"] = attempts + 1
            delay_ms = min(60000, 1000 * (2**attempts))
            ch.confirm_delivery()
            ch.basic_publish(
                exchange="",
                routing_key=retry_queue,
                body=body,
                properties=pika.BasicProperties(
                    content_type=properties.content_type or "application/json",
                    delivery_mode=2,
                    message_id=properties.message_id,
                    correlation_id=properties.correlation_id,
                    headers=headers,
                    expiration=str(delay_ms),
                ),
                mandatory=True,
            )
            ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_consume(
        queue=settings.rabbitmq_loan_queue or "", on_message_callback=callback, auto_ack=False
    )

    def stop(_signum: int, _frame: object) -> None:
        if connection.is_open:
            connection.add_callback_threadsafe(channel.stop_consuming)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        channel.start_consuming()
    finally:
        if connection.is_open:
            connection.close()
        engine.dispose()


if __name__ == "__main__":
    main()
