from __future__ import annotations

from abc import ABC, abstractmethod
from types import TracebackType
from typing import Any, Protocol, Self
from uuid import UUID

from lendup_reputation.domain.models import Evaluacion, PrestamoEvaluable


class EvaluacionRepository(ABC):
    @abstractmethod
    def get_evaluable_loan(self, prestamo_id: UUID) -> PrestamoEvaluable | None: ...

    @abstractmethod
    def has_rating(self, prestamo_id: UUID, evaluador_id: UUID) -> bool: ...

    @abstractmethod
    def add(self, evaluacion: Evaluacion) -> None: ...

    @abstractmethod
    def list_for_user(self, usuario_id: UUID) -> list[Evaluacion]: ...


class DomainEventPublisher(ABC):
    """Port that records an event in the transactional outbox."""

    @abstractmethod
    def register(self, event_type: str, event_id: UUID, payload: dict[str, Any]) -> None: ...


class UnitOfWork(Protocol):
    evaluaciones: EvaluacionRepository
    events: DomainEventPublisher

    def __enter__(self) -> Self: ...
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...
    def audit(
        self, action: str, actor_id: UUID, entity_id: UUID, details: dict[str, Any]
    ) -> None: ...


class IdentityResolver(Protocol):
    def resolve_internal_user_id(self, firebase_uid: str, bearer_token: str) -> UUID: ...


class TokenVerifier(Protocol):
    def verify(self, token: str) -> str: ...
