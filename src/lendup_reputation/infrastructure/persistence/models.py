from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class EvaluationModel(Base):
    __tablename__ = "evaluaciones"
    __table_args__ = (
        UniqueConstraint(
            "prestamo_id", "evaluador_usuario_id", name="uq_evaluacion_prestamo_evaluador"
        ),
        Index("ix_evaluaciones_evaluado_fecha", "evaluado_usuario_id", "registrada_en"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True, native_uuid=False), primary_key=True)
    prestamo_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True, native_uuid=False), nullable=False, index=True
    )
    evaluador_usuario_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True, native_uuid=False), nullable=False
    )
    evaluado_usuario_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True, native_uuid=False), nullable=False
    )
    puntaje: Mapped[int] = mapped_column(Integer, nullable=False)
    comentario: Mapped[str | None] = mapped_column(String(400))
    registrada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EvaluableLoanModel(Base):
    __tablename__ = "prestamos_evaluables"

    prestamo_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True, native_uuid=False), primary_key=True
    )
    prestamista_usuario_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True, native_uuid=False), nullable=False, index=True
    )
    prestatario_usuario_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True, native_uuid=False), nullable=False, index=True
    )
    finalizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_event_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True, native_uuid=False), nullable=False, unique=True
    )
    aggregate_version: Mapped[int | None] = mapped_column(BigInteger)
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OutboxEventModel(Base):
    __tablename__ = "outbox_events"
    __table_args__ = (Index("ix_outbox_pending", "published_at", "next_attempt_at"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True, native_uuid=False), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    claimed_by: Mapped[str | None] = mapped_column(String(100))
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProcessedEventModel(Base):
    __tablename__ = "processed_events"

    event_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True, native_uuid=False), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    aggregate_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True, native_uuid=False), nullable=False, index=True
    )
    aggregate_version: Mapped[int | None] = mapped_column(BigInteger)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AuditLogModel(Base):
    __tablename__ = "registro_auditoria"
    __table_args__ = (Index("ix_audit_actor_time", "actor_usuario_id", "registrada_en"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True, native_uuid=False), primary_key=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    actor_usuario_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True, native_uuid=False), nullable=False
    )
    entity_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True, native_uuid=False), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    registrada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
