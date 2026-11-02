from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from lendup_reputation.infrastructure.messaging.contracts import PrestamoFinalizadoV1


def valid_event() -> dict[str, object]:
    return {
        "event_id": str(uuid4()),
        "event_type": "PrestamoFinalizado",
        "event_version": 1,
        "prestamo_id": str(uuid4()),
        "prestamista_usuario_id": str(uuid4()),
        "prestatario_usuario_id": str(uuid4()),
        "finalizado_en": datetime.now(UTC).isoformat(),
        "correlation_id": str(uuid4()),
        "aggregate_version": 4,
    }


def test_valid_canonical_loan_event() -> None:
    assert PrestamoFinalizadoV1.model_validate(valid_event()).event_version == 1


@pytest.mark.parametrize(
    ("field", "value"),
    [("event_version", 2), ("event_type", "LoanFinished"), ("finalizado_en", "2026-01-01")],
)
def test_incompatible_or_invalid_event_is_rejected(field: str, value: object) -> None:
    event = valid_event()
    event[field] = value
    with pytest.raises(ValidationError):
        PrestamoFinalizadoV1.model_validate(event)


def test_unknown_external_fields_are_rejected() -> None:
    event = valid_event()
    event["invented"] = True
    with pytest.raises(ValidationError):
        PrestamoFinalizadoV1.model_validate(event)
