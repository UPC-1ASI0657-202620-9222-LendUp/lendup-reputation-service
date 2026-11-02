from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from lendup_reputation.domain.exceptions import InvalidCommentError, InvalidScoreError

MAX_COMMENT_LENGTH = 400


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class Evaluacion:
    id: UUID
    prestamo_id: UUID
    evaluador_usuario_id: UUID
    evaluado_usuario_id: UUID
    puntaje: int
    comentario: str | None
    registrada_en: datetime

    def __post_init__(self) -> None:
        if isinstance(self.puntaje, bool) or not isinstance(self.puntaje, int):
            raise InvalidScoreError("El puntaje debe ser un entero")
        if not 1 <= self.puntaje <= 5:
            raise InvalidScoreError("El puntaje debe estar entre 1 y 5")
        if self.comentario is not None and len(self.comentario) > MAX_COMMENT_LENGTH:
            raise InvalidCommentError(
                f"El comentario no puede superar {MAX_COMMENT_LENGTH} caracteres"
            )
        if self.registrada_en.tzinfo is None:
            raise ValueError("registrada_en debe incluir zona horaria UTC")

    @classmethod
    def registrar(
        cls,
        *,
        prestamo_id: UUID,
        evaluador_usuario_id: UUID,
        evaluado_usuario_id: UUID,
        puntaje: int,
        comentario: str | None,
        ahora: datetime | None = None,
    ) -> Evaluacion:
        normalized = comentario.strip() if comentario and comentario.strip() else None
        return cls(
            id=uuid4(),
            prestamo_id=prestamo_id,
            evaluador_usuario_id=evaluador_usuario_id,
            evaluado_usuario_id=evaluado_usuario_id,
            puntaje=puntaje,
            comentario=normalized,
            registrada_en=ahora or utc_now(),
        )


@dataclass(frozen=True, slots=True)
class PrestamoEvaluable:
    prestamo_id: UUID
    prestamista_usuario_id: UUID
    prestatario_usuario_id: UUID
    finalizado_en: datetime
    source_event_id: UUID
    aggregate_version: int | None = None

    def contraparte_de(self, usuario_id: UUID) -> UUID | None:
        if usuario_id == self.prestamista_usuario_id:
            return self.prestatario_usuario_id
        if usuario_id == self.prestatario_usuario_id:
            return self.prestamista_usuario_id
        return None


@dataclass(frozen=True, slots=True)
class ReputationSummary:
    usuario_id: UUID
    cantidad: int
    promedio: float
    calificaciones: tuple[Evaluacion, ...]
