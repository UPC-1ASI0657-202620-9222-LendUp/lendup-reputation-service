from __future__ import annotations

from collections.abc import Callable
from datetime import UTC
from uuid import UUID, uuid4

from lendup_reputation.application.ports import UnitOfWork
from lendup_reputation.domain.exceptions import DuplicateRatingError, LoanNotFoundError
from lendup_reputation.domain.models import Evaluacion, ReputationSummary
from lendup_reputation.domain.services import CalificacionValidator, ReputationCalculator


class ReputacionApplicationService:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        validator: CalificacionValidator | None = None,
        calculator: ReputationCalculator | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._validator = validator or CalificacionValidator()
        self._calculator = calculator or ReputationCalculator()

    def registrar_evaluacion(
        self,
        *,
        prestamo_id: UUID,
        evaluador_id: UUID,
        puntaje: int,
        comentario: str | None,
    ) -> Evaluacion:
        with self._uow_factory() as uow:
            prestamo = uow.evaluaciones.get_evaluable_loan(prestamo_id)
            if prestamo is None:
                raise LoanNotFoundError("Préstamo finalizado desconocido")
            evaluado_id = self._validator.validar(
                prestamo=prestamo,
                evaluador_id=evaluador_id,
                ya_evaluo=uow.evaluaciones.has_rating(prestamo_id, evaluador_id),
            )
            evaluacion = Evaluacion.registrar(
                prestamo_id=prestamo_id,
                evaluador_usuario_id=evaluador_id,
                evaluado_usuario_id=evaluado_id,
                puntaje=puntaje,
                comentario=comentario,
            )
            try:
                uow.evaluaciones.add(evaluacion)
                uow.audit(
                    "CALIFICACION_REGISTRADA",
                    evaluador_id,
                    evaluacion.id,
                    {"prestamo_id": str(prestamo_id), "evaluado_usuario_id": str(evaluado_id)},
                )
                event_id = uuid4()
                uow.events.register(
                    "CalificacionRegistrada.v1",
                    event_id,
                    {
                        "event_id": str(event_id),
                        "correlation_id": str(event_id),
                        "event_type": "CalificacionRegistrada",
                        "event_version": 1,
                        "evaluacion_id": str(evaluacion.id),
                        "prestamo_id": str(prestamo_id),
                        "evaluador_usuario_id": str(evaluador_id),
                        "evaluado_usuario_id": str(evaluado_id),
                        "puntaje": puntaje,
                        "registrada_en": (
                            evaluacion.registrada_en.astimezone(UTC)
                            .isoformat()
                            .replace("+00:00", "Z")
                        ),
                    },
                )
                uow.commit()
            except Exception as exc:
                if exc.__class__.__name__ == "IntegrityError":
                    raise DuplicateRatingError("Ya calificaste este préstamo") from exc
                raise
            return evaluacion

    def consultar_reputacion(self, usuario_id: UUID) -> ReputationSummary:
        with self._uow_factory() as uow:
            ratings = uow.evaluaciones.list_for_user(usuario_id)
        return self._calculator.calcular(usuario_id, ratings)
