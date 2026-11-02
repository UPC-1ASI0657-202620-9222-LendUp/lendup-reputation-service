from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from lendup_reputation.domain.exceptions import (
    DuplicateRatingError,
    NotLoanParticipantError,
    SelfRatingError,
)
from lendup_reputation.domain.models import Evaluacion, PrestamoEvaluable, ReputationSummary


class CalificacionValidator:
    """Enforces participation, counterparty and duplicate invariants."""

    def validar(
        self,
        *,
        prestamo: PrestamoEvaluable,
        evaluador_id: UUID,
        ya_evaluo: bool,
    ) -> UUID:
        contraparte = prestamo.contraparte_de(evaluador_id)
        if contraparte is None:
            raise NotLoanParticipantError("No participas en este préstamo")
        if contraparte == evaluador_id:
            raise SelfRatingError("No puedes evaluarte a ti mismo")
        if ya_evaluo:
            raise DuplicateRatingError("Ya calificaste este préstamo")
        return contraparte


class ReputationCalculator:
    """Calculates a deterministic half-up average rounded to one decimal."""

    def calcular(self, usuario_id: UUID, evaluaciones: list[Evaluacion]) -> ReputationSummary:
        ordered = tuple(
            sorted(
                evaluaciones,
                key=lambda item: (item.registrada_en, item.id),
                reverse=True,
            )
        )
        if not ordered:
            return ReputationSummary(usuario_id, 0, 0.0, ())
        total = sum(item.puntaje for item in ordered)
        average = (Decimal(total) / Decimal(len(ordered))).quantize(
            Decimal("0.1"), rounding=ROUND_HALF_UP
        )
        return ReputationSummary(usuario_id, len(ordered), float(average), ordered)
