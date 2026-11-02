from __future__ import annotations

from datetime import UTC

from sqlalchemy.orm import Session, sessionmaker

from lendup_reputation.domain.models import utc_now
from lendup_reputation.infrastructure.messaging.contracts import PrestamoFinalizadoV1
from lendup_reputation.infrastructure.persistence.models import (
    EvaluableLoanModel,
    ProcessedEventModel,
)


class IncompatibleEventError(ValueError):
    pass


class LoanProjectionConsumer:
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def process(self, event: PrestamoFinalizadoV1) -> bool:
        """Returns False for an already processed or stale event."""
        with self._factory.begin() as session:
            if session.get(ProcessedEventModel, event.event_id) is not None:
                return False
            existing = session.get(EvaluableLoanModel, event.prestamo_id)
            if (
                existing is not None
                and event.aggregate_version is not None
                and existing.aggregate_version is not None
                and event.aggregate_version <= existing.aggregate_version
            ):
                self._mark_processed(session, event)
                return False
            if existing is None:
                existing = EvaluableLoanModel(
                    prestamo_id=event.prestamo_id,
                    prestamista_usuario_id=event.prestamista_usuario_id,
                    prestatario_usuario_id=event.prestatario_usuario_id,
                    finalizado_en=event.finalizado_en.astimezone(UTC),
                    source_event_id=event.event_id,
                    aggregate_version=event.aggregate_version,
                    actualizado_en=utc_now(),
                )
                session.add(existing)
            else:
                existing.prestamista_usuario_id = event.prestamista_usuario_id
                existing.prestatario_usuario_id = event.prestatario_usuario_id
                existing.finalizado_en = event.finalizado_en.astimezone(UTC)
                existing.source_event_id = event.event_id
                existing.aggregate_version = event.aggregate_version
                existing.actualizado_en = utc_now()
            self._mark_processed(session, event)
        return True

    @staticmethod
    def _mark_processed(session: Session, event: PrestamoFinalizadoV1) -> None:
        session.add(
            ProcessedEventModel(
                event_id=event.event_id,
                event_type=f"{event.event_type}.v{event.event_version}",
                aggregate_id=event.prestamo_id,
                aggregate_version=event.aggregate_version,
                processed_at=utc_now(),
            )
        )
