from datetime import UTC, datetime
from uuid import uuid4

import pytest

from lendup_reputation.application.service import ReputacionApplicationService
from lendup_reputation.domain.exceptions import (
    DuplicateRatingError,
    LoanNotFoundError,
    NotLoanParticipantError,
    SelfRatingError,
)
from lendup_reputation.domain.models import PrestamoEvaluable
from tests.fakes import FakeUnitOfWork, MemoryStore


def setup_service(
    *, same_participant: bool = False
) -> tuple[ReputacionApplicationService, MemoryStore, PrestamoEvaluable]:
    store = MemoryStore()
    lender = uuid4()
    loan = PrestamoEvaluable(
        prestamo_id=uuid4(),
        prestamista_usuario_id=lender,
        prestatario_usuario_id=lender if same_participant else uuid4(),
        finalizado_en=datetime.now(UTC),
        source_event_id=uuid4(),
    )
    store.loans[loan.prestamo_id] = loan
    return ReputacionApplicationService(lambda: FakeUnitOfWork(store)), store, loan


def test_lender_rates_borrower_and_registers_atomic_artifacts() -> None:
    service, store, loan = setup_service()
    result = service.registrar_evaluacion(
        prestamo_id=loan.prestamo_id,
        evaluador_id=loan.prestamista_usuario_id,
        puntaje=5,
        comentario=" Excelente ",
    )
    assert result.evaluado_usuario_id == loan.prestatario_usuario_id
    assert result.comentario == "Excelente"
    assert len(store.ratings) == len(store.events) == len(store.audits) == 1
    assert "evaluado_usuario_id" in store.events[0][2]


def test_borrower_rates_lender() -> None:
    service, _, loan = setup_service()
    result = service.registrar_evaluacion(
        prestamo_id=loan.prestamo_id,
        evaluador_id=loan.prestatario_usuario_id,
        puntaje=4,
        comentario=None,
    )
    assert result.evaluado_usuario_id == loan.prestamista_usuario_id


def test_both_participants_can_rate_once() -> None:
    service, store, loan = setup_service()
    for user in (loan.prestamista_usuario_id, loan.prestatario_usuario_id):
        service.registrar_evaluacion(
            prestamo_id=loan.prestamo_id, evaluador_id=user, puntaje=5, comentario=None
        )
    assert len(store.ratings) == 2


def test_third_party_is_rejected() -> None:
    service, _, loan = setup_service()
    with pytest.raises(NotLoanParticipantError):
        service.registrar_evaluacion(
            prestamo_id=loan.prestamo_id,
            evaluador_id=uuid4(),
            puntaje=5,
            comentario=None,
        )


def test_unknown_or_not_finalized_loan_without_projection_is_rejected() -> None:
    service, _, loan = setup_service()
    with pytest.raises(LoanNotFoundError):
        service.registrar_evaluacion(
            prestamo_id=uuid4(),
            evaluador_id=loan.prestamista_usuario_id,
            puntaje=5,
            comentario=None,
        )


def test_duplicate_is_rejected() -> None:
    service, _, loan = setup_service()
    kwargs = {
        "prestamo_id": loan.prestamo_id,
        "evaluador_id": loan.prestamista_usuario_id,
        "puntaje": 5,
        "comentario": None,
    }
    service.registrar_evaluacion(**kwargs)
    with pytest.raises(DuplicateRatingError):
        service.registrar_evaluacion(**kwargs)


def test_self_rating_is_rejected_for_corrupt_projection() -> None:
    service, _, loan = setup_service(same_participant=True)
    with pytest.raises(SelfRatingError):
        service.registrar_evaluacion(
            prestamo_id=loan.prestamo_id,
            evaluador_id=loan.prestamista_usuario_id,
            puntaje=5,
            comentario=None,
        )
