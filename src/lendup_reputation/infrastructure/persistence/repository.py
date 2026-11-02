from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from lendup_reputation.application.ports import DomainEventPublisher, EvaluacionRepository
from lendup_reputation.domain.models import Evaluacion, PrestamoEvaluable, utc_now
from lendup_reputation.infrastructure.persistence.models import (
    AuditLogModel,
    EvaluableLoanModel,
    EvaluationModel,
    OutboxEventModel,
)


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


class EvaluacionRepositoryImpl(EvaluacionRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_evaluable_loan(self, prestamo_id: UUID) -> PrestamoEvaluable | None:
        row = self._session.get(EvaluableLoanModel, prestamo_id)
        if row is None:
            return None
        return PrestamoEvaluable(
            prestamo_id=UUID(str(row.prestamo_id)),
            prestamista_usuario_id=UUID(str(row.prestamista_usuario_id)),
            prestatario_usuario_id=UUID(str(row.prestatario_usuario_id)),
            finalizado_en=_aware(row.finalizado_en),
            source_event_id=UUID(str(row.source_event_id)),
            aggregate_version=row.aggregate_version,
        )

    def has_rating(self, prestamo_id: UUID, evaluador_id: UUID) -> bool:
        statement = select(EvaluationModel.id).where(
            EvaluationModel.prestamo_id == prestamo_id,
            EvaluationModel.evaluador_usuario_id == evaluador_id,
        )
        return self._session.scalar(statement) is not None

    def add(self, evaluacion: Evaluacion) -> None:
        self._session.add(
            EvaluationModel(
                id=evaluacion.id,
                prestamo_id=evaluacion.prestamo_id,
                evaluador_usuario_id=evaluacion.evaluador_usuario_id,
                evaluado_usuario_id=evaluacion.evaluado_usuario_id,
                puntaje=evaluacion.puntaje,
                comentario=evaluacion.comentario,
                registrada_en=evaluacion.registrada_en,
            )
        )
        self._session.flush()

    def list_for_user(self, usuario_id: UUID) -> list[Evaluacion]:
        statement = (
            select(EvaluationModel)
            .where(EvaluationModel.evaluado_usuario_id == usuario_id)
            .order_by(EvaluationModel.registrada_en.desc(), EvaluationModel.id.desc())
        )
        return [self._to_domain(row) for row in self._session.scalars(statement)]

    @staticmethod
    def _to_domain(row: EvaluationModel) -> Evaluacion:
        return Evaluacion(
            id=UUID(str(row.id)),
            prestamo_id=UUID(str(row.prestamo_id)),
            evaluador_usuario_id=UUID(str(row.evaluador_usuario_id)),
            evaluado_usuario_id=UUID(str(row.evaluado_usuario_id)),
            puntaje=row.puntaje,
            comentario=row.comentario,
            registrada_en=_aware(row.registrada_en),
        )


class SqlAlchemyDomainEventPublisher(DomainEventPublisher):
    def __init__(self, session: Session) -> None:
        self._session = session

    def register(self, event_type: str, event_id: UUID, payload: dict[str, Any]) -> None:
        self._session.add(
            OutboxEventModel(
                id=event_id,
                event_type=event_type,
                payload=payload,
                occurred_at=utc_now(),
                attempts=0,
            )
        )


class SqlAlchemyUnitOfWork:
    evaluaciones: EvaluacionRepository
    events: DomainEventPublisher

    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory
        self.session: Session

    def __enter__(self) -> SqlAlchemyUnitOfWork:
        self.session = self._factory()
        self.evaluaciones = EvaluacionRepositoryImpl(self.session)
        self.events = SqlAlchemyDomainEventPublisher(self.session)
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if exc_type is not None:
            self.rollback()
        self.session.close()

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()

    def audit(self, action: str, actor_id: UUID, entity_id: UUID, details: dict[str, Any]) -> None:
        self.session.add(
            AuditLogModel(
                id=uuid4(),
                action=action,
                actor_usuario_id=actor_id,
                entity_id=entity_id,
                details=details,
                registrada_en=utc_now(),
            )
        )
