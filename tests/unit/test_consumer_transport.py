from types import SimpleNamespace
from typing import Any

import pika
from pika.exceptions import AMQPConnectionError

from lendup_reputation.config.settings import Settings
from lendup_reputation.infrastructure.messaging.consumer import RabbitMqLoanConsumer
from tests.unit.test_contracts import valid_event


class RecordingChannel:
    def __init__(self, sequence: list[str]) -> None:
        self.sequence = sequence
        self.acks: list[int] = []
        self.rejects: list[tuple[int, bool]] = []
        self.published: list[dict[str, Any]] = []
        self.declarations: list[tuple[str, dict[str, Any]]] = []

    def basic_ack(self, *, delivery_tag: int) -> None:
        self.sequence.append("ack")
        self.acks.append(delivery_tag)

    def basic_reject(self, *, delivery_tag: int, requeue: bool) -> None:
        self.sequence.append("reject")
        self.rejects.append((delivery_tag, requeue))

    def confirm_delivery(self) -> None:
        self.sequence.append("confirm")

    def basic_publish(self, **kwargs: Any) -> None:
        self.sequence.append("publish")
        self.published.append(kwargs)

    def exchange_declare(self, **kwargs: Any) -> None:
        self.declarations.append(("exchange", kwargs))

    def queue_declare(self, **kwargs: Any) -> None:
        self.declarations.append(("queue", kwargs))

    def queue_bind(self, **kwargs: Any) -> None:
        self.declarations.append(("bind", kwargs))

    def basic_qos(self, **kwargs: Any) -> None:
        self.declarations.append(("qos", kwargs))


class Processor:
    def __init__(self, sequence: list[str], *, fail: bool = False) -> None:
        self.sequence = sequence
        self.fail = fail

    def process(self, _event: object) -> bool:
        self.sequence.append("commit" if not self.fail else "rollback")
        if self.fail:
            raise RuntimeError("transient database failure")
        return True


def settings(**overrides: Any) -> Settings:
    return Settings(
        firebase_project_id="lendup-desarrollo",
        rabbitmq_exchange="events",
        rabbitmq_loan_queue="reputation.loans",
        rabbitmq_loan_routing_key="loans.finalized",
        rabbitmq_dlq="reputation.loans.dlq",
        **overrides,
    )


def delivery_body() -> bytes:
    import json

    return json.dumps(valid_event()).encode()


def test_ack_happens_only_after_processor_commit() -> None:
    sequence: list[str] = []
    channel = RecordingChannel(sequence)
    consumer = RabbitMqLoanConsumer(settings(), Processor(sequence))
    consumer.handle_delivery(
        channel,
        SimpleNamespace(delivery_tag=7),
        pika.BasicProperties(correlation_id="correlation"),
        delivery_body(),
    )
    assert sequence == ["commit", "ack"]
    assert channel.acks == [7]


def test_transient_failure_publishes_durable_retry_before_ack_and_preserves_correlation() -> None:
    sequence: list[str] = []
    channel = RecordingChannel(sequence)
    consumer = RabbitMqLoanConsumer(settings(), Processor(sequence, fail=True))
    consumer.handle_delivery(
        channel,
        SimpleNamespace(delivery_tag=8),
        pika.BasicProperties(correlation_id="correlation", headers={"x-lendup-retry": 1}),
        delivery_body(),
    )
    assert sequence == ["rollback", "confirm", "publish", "ack"]
    properties = channel.published[0]["properties"]
    assert properties.delivery_mode == 2
    assert properties.correlation_id == "correlation"
    assert properties.headers["x-lendup-retry"] == 2


def test_retry_limit_and_invalid_payload_use_dlq_without_ack() -> None:
    sequence: list[str] = []
    channel = RecordingChannel(sequence)
    consumer = RabbitMqLoanConsumer(
        settings(consumer_max_retries=2), Processor(sequence, fail=True)
    )
    consumer.handle_delivery(
        channel,
        SimpleNamespace(delivery_tag=9),
        pika.BasicProperties(headers={"x-lendup-retry": 2}),
        delivery_body(),
    )
    consumer.handle_delivery(
        channel,
        SimpleNamespace(delivery_tag=10),
        pika.BasicProperties(),
        b"not-json",
    )
    assert channel.acks == []
    assert channel.rejects == [(9, False), (10, False)]


def test_topology_is_durable_and_connection_retries_with_backoff() -> None:
    sequence: list[str] = []
    channel = RecordingChannel(sequence)
    consumer = RabbitMqLoanConsumer(settings(), Processor(sequence))
    consumer._configure_channel(channel)
    queue_declarations = [item for kind, item in channel.declarations if kind == "queue"]
    assert len(queue_declarations) == 3
    assert all(item["durable"] is True for item in queue_declarations)

    delays: list[float] = []
    calls = 0

    def consume_once() -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise AMQPConnectionError("disconnected")
        consumer.stop()

    consumer._consume_once = consume_once  # type: ignore[method-assign]
    consumer._sleeper = delays.append
    consumer.run_forever()
    assert calls == 2
    assert delays == [1.0]
