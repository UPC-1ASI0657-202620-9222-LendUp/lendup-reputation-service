from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from alembic.config import Config
from sqlalchemy import Engine, func, inspect, select
from testcontainers.mysql import MySqlContainer

from alembic import command
from lendup_reputation.application.service import ReputacionApplicationService
from lendup_reputation.config.settings import Settings, get_settings
from lendup_reputation.domain.exceptions import DuplicateRatingError
from lendup_reputation.infrastructure.messaging.contracts import PrestamoFinalizadoV1
from lendup_reputation.infrastructure.messaging.inbox import LoanProjectionConsumer
from lendup_reputation.infrastructure.messaging.outbox import OutboxPublisher
from lendup_reputation.infrastructure.persistence.database import (
    create_database_engine,
    create_session_factory,
)
from lendup_reputation.infrastructure.persistence.models import (
    EvaluableLoanModel,
    EvaluationModel,
    OutboxEventModel,
    ProcessedEventModel,
)
from lendup_reputation.infrastructure.persistence.repository import SqlAlchemyUnitOfWork

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def mysql_engine() -> Engine:
    if os.getenv("RUN_INTEGRATION") != "1":
        pytest.skip("Set RUN_INTEGRATION=1 to run Docker-backed integration tests")
    with MySqlContainer("mysql:8.4") as mysql:
        url = mysql.get_connection_url().replace("mysql://", "mysql+pymysql://", 1)
        os.environ["DATABASE_URL"] = url
        get_settings.cache_clear()
        config = Config("alembic.ini")
        command.upgrade(config, "head")
        engine = create_database_engine(
            Settings(firebase_project_id="lendup-desarrollo", database_url=url)
        )
        yield engine
        engine.dispose()


def event() -> PrestamoFinalizadoV1:
    return PrestamoFinalizadoV1(
        event_id=uuid4(),
        event_type="PrestamoFinalizado",
        event_version=1,
        prestamo_id=uuid4(),
        prestamista_usuario_id=uuid4(),
        prestatario_usuario_id=uuid4(),
        finalizado_en=datetime.now(UTC),
        correlation_id=uuid4(),
        aggregate_version=1,
    )


def test_migrations_create_all_required_tables(mysql_engine: Engine) -> None:
    tables = set(inspect(mysql_engine).get_table_names())
    assert {
        "evaluaciones",
        "prestamos_evaluables",
        "outbox_events",
        "processed_events",
        "registro_auditoria",
    } <= tables


def test_inbox_is_idempotent_and_stale_event_is_ignored(mysql_engine: Engine) -> None:
    factory = create_session_factory(mysql_engine)
    consumer = LoanProjectionConsumer(factory)
    original = event()
    assert consumer.process(original) is True
    assert consumer.process(original) is False
    stale = original.model_copy(
        update={"event_id": uuid4(), "aggregate_version": 0, "correlation_id": uuid4()}
    )
    assert consumer.process(stale) is False
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(ProcessedEventModel)) >= 2
        projected = session.get(EvaluableLoanModel, original.prestamo_id)
        assert projected is not None and projected.aggregate_version == 1


def test_unversioned_redelivery_cannot_replace_versioned_projection(mysql_engine: Engine) -> None:
    factory = create_session_factory(mysql_engine)
    consumer = LoanProjectionConsumer(factory)
    original = event()
    assert consumer.process(original) is True
    unversioned = original.model_copy(
        update={
            "event_id": uuid4(),
            "aggregate_version": None,
            "prestamista_usuario_id": uuid4(),
            "correlation_id": uuid4(),
        }
    )
    assert consumer.process(unversioned) is False
    with factory() as session:
        projected = session.get(EvaluableLoanModel, original.prestamo_id)
        assert projected is not None
        assert projected.prestamista_usuario_id == original.prestamista_usuario_id
        assert session.get(ProcessedEventModel, unversioned.event_id) is not None


def test_concurrent_rating_has_one_commit_and_one_logical_event(mysql_engine: Engine) -> None:
    factory = create_session_factory(mysql_engine)
    loan = event()
    LoanProjectionConsumer(factory).process(loan)
    service = ReputacionApplicationService(lambda: SqlAlchemyUnitOfWork(factory))

    def rate() -> str:
        try:
            service.registrar_evaluacion(
                prestamo_id=loan.prestamo_id,
                evaluador_id=loan.prestamista_usuario_id,
                puntaje=5,
                comentario="Concurrente",
            )
            return "created"
        except DuplicateRatingError:
            return "duplicate"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: rate(), range(2)))
    assert sorted(results) == ["created", "duplicate"]
    with factory() as session:
        ratings = session.scalar(
            select(func.count())
            .select_from(EvaluationModel)
            .where(
                EvaluationModel.prestamo_id == loan.prestamo_id,
                EvaluationModel.evaluador_usuario_id == loan.prestamista_usuario_id,
            )
        )
        events = session.scalar(
            select(func.count())
            .select_from(OutboxEventModel)
            .where(OutboxEventModel.payload["prestamo_id"].as_string() == str(loan.prestamo_id))
        )
        assert ratings == 1
        assert events == 1


def test_outbox_is_recoverable_after_transient_broker_failure(mysql_engine: Engine) -> None:
    factory = create_session_factory(mysql_engine)
    outbox_id = uuid4()
    with factory.begin() as session:
        session.add(
            OutboxEventModel(
                id=outbox_id,
                event_type="CalificacionRegistrada.v1",
                payload={"event_id": str(outbox_id), "event_type": "CalificacionRegistrada"},
                occurred_at=datetime.now(UTC),
                attempts=0,
            )
        )

    class Broker:
        fail = True
        published = 0

        def publish(self, _payload: object, _event_id: object) -> None:
            if self.fail:
                raise RuntimeError("broker unavailable")
            self.published += 1

    broker = Broker()
    publisher = OutboxPublisher(
        factory,
        broker,
        Settings(firebase_project_id="lendup-desarrollo"),
    )  # type: ignore[arg-type]
    assert publisher.publish_batch() == 0
    with factory.begin() as session:
        row = session.get(OutboxEventModel, outbox_id, with_for_update=True)
        assert row is not None and row.attempts == 1 and row.published_at is None
        row.next_attempt_at = datetime.now(UTC) - timedelta(seconds=1)
    broker.fail = False
    assert publisher.publish_batch() == 1
    with factory() as session:
        row = session.get(OutboxEventModel, outbox_id)
        assert row is not None and row.published_at is not None
    assert broker.published == 1
