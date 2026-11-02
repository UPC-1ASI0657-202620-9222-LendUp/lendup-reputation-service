from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from lendup_reputation.domain.exceptions import InvalidCommentError, InvalidScoreError
from lendup_reputation.domain.models import Evaluacion
from lendup_reputation.domain.services import ReputationCalculator


def rating(score: object, comment: str | None = None, *, seconds: int = 0) -> Evaluacion:
    return Evaluacion(
        id=uuid4(),
        prestamo_id=uuid4(),
        evaluador_usuario_id=uuid4(),
        evaluado_usuario_id=uuid4(),
        puntaje=score,  # type: ignore[arg-type]
        comentario=comment,
        registrada_en=datetime(2026, 11, 2, tzinfo=UTC) + timedelta(seconds=seconds),
    )


@pytest.mark.parametrize("score", [1, 2, 3, 4, 5])
def test_accepts_scores_from_one_to_five(score: int) -> None:
    assert rating(score).puntaje == score


@pytest.mark.parametrize("score", [0, 6, -1])
def test_rejects_score_outside_range(score: int) -> None:
    with pytest.raises(InvalidScoreError):
        rating(score)


@pytest.mark.parametrize("score", [2.5, "5", True, None])
def test_rejects_non_integer_score(score: object) -> None:
    with pytest.raises(InvalidScoreError):
        rating(score)


def test_optional_comment_and_length_policy() -> None:
    assert rating(5).comentario is None
    assert rating(5, "x" * 400).comentario == "x" * 400
    with pytest.raises(InvalidCommentError):
        rating(5, "x" * 401)


def test_empty_reputation() -> None:
    user_id = uuid4()
    result = ReputationCalculator().calcular(user_id, [])
    assert (result.cantidad, result.promedio, result.calificaciones) == (0, 0.0, ())


def test_average_count_rounding_and_deterministic_order() -> None:
    user_id = uuid4()
    older = rating(4, seconds=1)
    newer = rating(5, seconds=2)
    result = ReputationCalculator().calcular(user_id, [older, newer, rating(4)])
    assert result.cantidad == 3
    assert result.promedio == 4.3
    assert result.calificaciones[0] == newer
    assert result.calificaciones[1] == older
