from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RatingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    puntaje: int = Field(ge=1, le=5, strict=True)
    comentario: str | None = Field(default=None, max_length=400)


class RatingResponse(BaseModel):
    id: UUID
    prestamo_id: UUID
    evaluador_usuario_id: UUID
    evaluado_usuario_id: UUID
    puntaje: int
    comentario: str | None
    registrada_en: datetime


class ReputationResponse(BaseModel):
    usuario_id: UUID
    cantidad: int
    promedio: float
    calificaciones: list[RatingResponse]


class ErrorBody(BaseModel):
    code: str
    message: str
    correlation_id: str


class ErrorResponse(BaseModel):
    error: ErrorBody
