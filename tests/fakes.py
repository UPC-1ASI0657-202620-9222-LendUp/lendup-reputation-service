from __future__ import annotations

from types import TracebackType
from typing import Any, Self
from uuid import UUID

from lendup_reputation.application.ports import DomainEventPublisher, EvaluacionRepository
from lendup_reputation.domain.models import Evaluacion, PrestamoEvaluable


class MemoryStore:
    def __init__(self) -> None:
        self.loans: dict[UUID, PrestamoEvaluable] = {}
        self.ratings: list[Evaluacion] = []
        self.events: list[tuple[str, UUID, dict[str, Any]]] = []
        self.audits: list[tuple[str, UUID, UUID, dict[str, Any]]] = []


class FakeRepository(EvaluacionRepository):
    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    def get_evaluable_loan(self, prestamo_id: UUID) -> PrestamoEvaluable | None:
        return self.store.loans.get(prestamo_id)

    def has_rating(self, prestamo_id: UUID, evaluador_id: UUID) -> bool:
        return any(
            item.prestamo_id == prestamo_id and item.evaluador_usuario_id == evaluador_id
            for item in self.store.ratings
        )

    def add(self, evaluacion: Evaluacion) -> None:
        self.store.ratings.append(evaluacion)

    def list_for_user(self, usuario_id: UUID) -> list[Evaluacion]:
        return [item for item in self.store.ratings if item.evaluado_usuario_id == usuario_id]


class FakePublisher(DomainEventPublisher):
    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    def register(self, event_type: str, event_id: UUID, payload: dict[str, Any]) -> None:
        self.store.events.append((event_type, event_id, payload))


class FakeUnitOfWork:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store
        self.evaluaciones = FakeRepository(store)
        self.events = FakePublisher(store)
        self.committed = False

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if exc_type:
            self.rollback()

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.committed = False

    def audit(self, action: str, actor_id: UUID, entity_id: UUID, details: dict[str, Any]) -> None:
        self.store.audits.append((action, actor_id, entity_id, details))
