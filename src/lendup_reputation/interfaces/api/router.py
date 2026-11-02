from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from lendup_reputation.application.service import ReputacionApplicationService
from lendup_reputation.domain.models import Evaluacion
from lendup_reputation.interfaces.api.dependencies import AuthenticatedUser, get_current_user
from lendup_reputation.interfaces.api.schemas import (
    ErrorResponse,
    RatingRequest,
    RatingResponse,
    ReputationResponse,
)

router = APIRouter(prefix="/api/v1", tags=["Reputación"])


def _service(request: Request) -> ReputacionApplicationService:
    return cast(ReputacionApplicationService, request.app.state.application_service)


def _rating_response(item: Evaluacion) -> RatingResponse:
    return RatingResponse(
        id=item.id,
        prestamo_id=item.prestamo_id,
        evaluador_usuario_id=item.evaluador_usuario_id,
        evaluado_usuario_id=item.evaluado_usuario_id,
        puntaje=item.puntaje,
        comentario=item.comentario,
        registrada_en=item.registrada_en,
    )


@router.post(
    "/prestamos/{id}/calificaciones",
    response_model=RatingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Calificar una experiencia de préstamo finalizada",
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def register_rating(
    id: UUID,
    body: RatingRequest,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
) -> RatingResponse:
    rating = _service(request).registrar_evaluacion(
        prestamo_id=id,
        evaluador_id=user.internal_user_id,
        puntaje=body.puntaje,
        comentario=body.comentario,
    )
    return _rating_response(rating)


@router.get(
    "/estudiantes/{id}/reputacion",
    response_model=ReputationResponse,
    summary="Consultar reputación de un estudiante",
    responses={
        401: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def get_reputation(
    id: UUID,
    request: Request,
    _user: AuthenticatedUser = Depends(get_current_user),
) -> ReputationResponse:
    summary = _service(request).consultar_reputacion(id)
    return ReputationResponse(
        usuario_id=summary.usuario_id,
        cantidad=summary.cantidad,
        promedio=summary.promedio,
        calificaciones=[_rating_response(item) for item in summary.calificaciones],
    )
