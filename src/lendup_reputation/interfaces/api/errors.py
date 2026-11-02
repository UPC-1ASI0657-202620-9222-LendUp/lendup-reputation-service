from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError

from lendup_reputation.domain.exceptions import (
    AuthenticationError,
    DomainError,
    DuplicateRatingError,
    IdentityNotResolvedError,
    IdentityUnavailableError,
    InvalidCommentError,
    InvalidScoreError,
    LoanNotFinalizedError,
    LoanNotFoundError,
    NotLoanParticipantError,
    SelfRatingError,
)


def _response(request: Request, status: int, code: str, message: str) -> JSONResponse:
    correlation_id = getattr(request.state, "correlation_id", str(uuid4()))
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "correlation_id": correlation_id}},
    )


def register_error_handlers(app: FastAPI) -> None:
    mappings: list[tuple[type[DomainError], int, str]] = [
        (AuthenticationError, 401, "AUTHENTICATION_FAILED"),
        (IdentityNotResolvedError, 403, "IDENTITY_NOT_RESOLVED"),
        (IdentityUnavailableError, 503, "IDENTITY_UNAVAILABLE"),
        (LoanNotFoundError, 404, "LOAN_NOT_FOUND"),
        (NotLoanParticipantError, 403, "NOT_LOAN_PARTICIPANT"),
        (SelfRatingError, 403, "SELF_RATING_FORBIDDEN"),
        (LoanNotFinalizedError, 409, "LOAN_NOT_FINALIZED"),
        (DuplicateRatingError, 409, "RATING_ALREADY_EXISTS"),
        (InvalidScoreError, 422, "INVALID_SCORE"),
        (InvalidCommentError, 422, "INVALID_COMMENT"),
    ]
    for exception_type, status_code, code in mappings:

        async def handler(
            request: Request,
            exc: Exception,
            *,
            _status: int = status_code,
            _code: str = code,
        ) -> JSONResponse:
            return _response(request, _status, _code, str(exc))

        app.add_exception_handler(exception_type, handler)

    async def validation_handler(request: Request, exc: Exception) -> JSONResponse:
        return _response(request, 422, "VALIDATION_ERROR", "Solicitud inválida")

    app.add_exception_handler(RequestValidationError, validation_handler)

    async def persistence_handler(request: Request, exc: Exception) -> JSONResponse:
        return _response(
            request, 503, "PERSISTENCE_UNAVAILABLE", "La persistencia no está disponible"
        )

    app.add_exception_handler(OperationalError, persistence_handler)
