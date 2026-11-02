from __future__ import annotations

import json
import os
from uuid import uuid4

import pika
import pytest
from testcontainers.rabbitmq import RabbitMqContainer

from lendup_reputation.config.settings import Settings
from lendup_reputation.infrastructure.messaging.outbox import MessageBrokerAdapter

pytestmark = pytest.mark.integration


def test_message_broker_publishes_persistent_confirmed_message() -> None:
    if os.getenv("RUN_INTEGRATION") != "1":
        pytest.skip("Set RUN_INTEGRATION=1 to run Docker-backed integration tests")
    with RabbitMqContainer("rabbitmq:4.1-management") as rabbit:
        url = (
            f"amqp://{rabbit.username}:{rabbit.password}@"
            f"{rabbit.get_container_host_ip()}:{rabbit.get_exposed_port(rabbit.port)}/%2F"
        )
        exchange = "test.events"
        queue = "test.rating"
        routing_key = "rating.registered.v1"
        connection = pika.BlockingConnection(pika.URLParameters(url))
        channel = connection.channel()
        channel.exchange_declare(exchange=exchange, exchange_type="topic", durable=True)
        channel.queue_declare(queue=queue, durable=True)
        channel.queue_bind(queue=queue, exchange=exchange, routing_key=routing_key)
        connection.close()
        settings = Settings(
            rabbitmq_url=url,
            rabbitmq_exchange=exchange,
            rabbitmq_rating_routing_key=routing_key,
        )
        event_id = uuid4()
        MessageBrokerAdapter(settings).publish(
            {"event_id": str(event_id), "event_type": "CalificacionRegistrada"}, event_id
        )
        connection = pika.BlockingConnection(pika.URLParameters(url))
        method, properties, body = connection.channel().basic_get(queue=queue, auto_ack=True)
        connection.close()
        assert method is not None
        assert properties.delivery_mode == 2
        assert properties.message_id == str(event_id)
        assert json.loads(body)["event_id"] == str(event_id)
