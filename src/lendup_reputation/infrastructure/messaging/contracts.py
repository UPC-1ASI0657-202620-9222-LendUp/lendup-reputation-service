from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PrestamoFinalizadoV1(BaseModel):
    """Provisional internal canonical schema; the external adapter is pending validation."""

    model_config = ConfigDict(extra="forbid")

    event_id: UUID
    event_type: Literal["PrestamoFinalizado"]
    event_version: Literal[1]
    prestamo_id: UUID
    prestamista_usuario_id: UUID
    prestatario_usuario_id: UUID
    finalizado_en: datetime
    correlation_id: UUID
    aggregate_version: int | None = Field(default=None, ge=0)

    @field_validator("finalizado_en")
    @classmethod
    def timestamp_must_be_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("finalizado_en debe incluir zona horaria")
        return value
