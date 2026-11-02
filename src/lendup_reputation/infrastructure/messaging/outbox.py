from __future__ import annotations

import json
import socket
from datetime import timedelta
from uuid import UUID

import pika
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, sessionmaker

from lendup_reputation.config.settings import Settings
from lendup_reputation.domain.models import utc_now
from lendup_reputation.infrastructure.persistence.models import OutboxEventModel


class BrokerPublishError(RuntimeError):
    pass


class MessageBrokerAdapter:
    """RabbitMQ adapter using durable delivery and publisher confirms."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def publish(self, payload: dict[str, object], event_id: UUID) -> None:
        self._settings.validate_worker_configuration("outbox")
        parameters = pika.URLParameters(self._settings.rabbitmq_url.get_secret_value())
        connection = pika.BlockingConnection(parameters)
        try:
            channel = connection.channel()
            channel.confirm_delivery()
            channel.basic_publish(
                exchange=self._settings.rabbitmq_exchange or "",
                routing_key=self._settings.rabbitmq_rating_routing_key or "",
                body=json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode(),
                properties=pika.BasicProperties(
                    content_type="application/json",
                    delivery_mode=2,
                    message_id=str(event_id),
                    correlation_id=str(payload.get("correlation_id", event_id)),
                    type=str(payload.get("event_type", "CalificacionRegistrada")),
                ),
                mandatory=True,
            )
        finally:
            if connection.is_open:
                connection.close()


class OutboxPublisher:
    def __init__(
        self,
        factory: sessionmaker[Session],
        broker: MessageBrokerAdapter,
        settings: Settings,
        worker_id: str | None = None,
    ) -> None:
        self._factory = factory
        self._broker = broker
        self._settings = settings
        self._worker_id = worker_id or socket.gethostname()

    def publish_batch(self) -> int:
        now = utc_now()
        with self._factory.begin() as session:
            statement = (
                select(OutboxEventModel)
                .where(
                    OutboxEventModel.published_at.is_(None),
                    or_(
                        OutboxEventModel.next_attempt_at.is_(None),
                        OutboxEventModel.next_attempt_at <= now,
                    ),
                    or_(
                        OutboxEventModel.claimed_at.is_(None),
                        OutboxEventModel.claimed_at < now - timedelta(minutes=5),
                    ),
                )
                .order_by(OutboxEventModel.occurred_at)
                .limit(self._settings.outbox_batch_size)
                .with_for_update(skip_locked=True)
            )
            events = list(session.scalars(statement))
            for event in events:
                event.claimed_by = self._worker_id
                event.claimed_at = now

        published = 0
        for claimed in events:
            try:
                self._broker.publish(claimed.payload, UUID(str(claimed.id)))
            except Exception as exc:
                with self._factory.begin() as session:
                    current = session.get(OutboxEventModel, claimed.id, with_for_update=True)
                    if current is not None and current.published_at is None:
                        current.attempts += 1
                        delay = min(300, 2 ** min(current.attempts, 8))
                        current.next_attempt_at = utc_now() + timedelta(seconds=delay)
                        current.last_error = str(exc)[:2000]
                        current.claimed_by = None
                        current.claimed_at = None
                continue
            with self._factory.begin() as session:
                current = session.get(OutboxEventModel, claimed.id, with_for_update=True)
                if current is not None and current.published_at is None:
                    current.published_at = utc_now()
                    current.claimed_by = None
                    current.claimed_at = None
                    published += 1
        return published
