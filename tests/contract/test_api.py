from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from lendup_reputation.application.service import ReputacionApplicationService
from lendup_reputation.config.settings import Settings
from lendup_reputation.domain.models import PrestamoEvaluable
from lendup_reputation.main import create_app
from tests.fakes import FakeUnitOfWork, MemoryStore


class TokenVerifier:
    def verify(self, token: str) -> str:
        if token != "valid":
            from lendup_reputation.domain.exceptions import AuthenticationError

            raise AuthenticationError("Token Firebase no válido")
        return "firebase-user"


class Resolver:
    def __init__(self, user_id: UUID) -> None:
        self.user_id = user_id

    def resolve_internal_user_id(self, firebase_uid: str, bearer_token: str) -> UUID:
        return self.user_id


def client_and_context() -> tuple[TestClient, MemoryStore, PrestamoEvaluable]:
    store = MemoryStore()
    lender = uuid4()
    loan = PrestamoEvaluable(
        prestamo_id=uuid4(),
        prestamista_usuario_id=lender,
        prestatario_usuario_id=uuid4(),
        finalizado_en=datetime.now(UTC),
        source_event_id=uuid4(),
    )
    store.loans[loan.prestamo_id] = loan
    app = create_app(
        Settings(
            firebase_project_id="lendup-desarrollo",
            database_url="mysql+pymysql://unused:unused@localhost:3307/unused",
            docs_enabled=True,
        )
    )
    app.state.application_service = ReputacionApplicationService(lambda: FakeUnitOfWork(store))
    app.state.token_verifier = TokenVerifier()
    app.state.identity_resolver = Resolver(lender)
    return TestClient(app), store, loan


def test_exact_routes_and_response_fields() -> None:
    client, _, loan = client_and_context()
    response = client.post(
        f"/api/v1/prestamos/{loan.prestamo_id}/calificaciones",
        json={"puntaje": 5, "comentario": "Excelente experiencia"},
        headers={"Authorization": "Bearer valid"},
    )
    assert response.status_code == 201
    assert set(response.json()) == {
        "id",
        "prestamo_id",
        "evaluador_usuario_id",
        "evaluado_usuario_id",
        "puntaje",
        "comentario",
        "registrada_en",
    }

    reputation = client.get(
        f"/api/v1/estudiantes/{loan.prestatario_usuario_id}/reputacion",
        headers={"Authorization": "Bearer valid"},
    )
    assert reputation.status_code == 200
    assert set(reputation.json()) == {"usuario_id", "cantidad", "promedio", "calificaciones"}
    assert reputation.json()["cantidad"] == 1


def test_user_without_ratings_contract() -> None:
    client, _, _ = client_and_context()
    user_id = uuid4()
    response = client.get(
        f"/api/v1/estudiantes/{user_id}/reputacion",
        headers={"Authorization": "Bearer valid"},
    )
    assert response.json() == {
        "usuario_id": str(user_id),
        "cantidad": 0,
        "promedio": 0.0,
        "calificaciones": [],
    }


def test_no_bearer_and_invalid_bearer_are_401() -> None:
    client, _, loan = client_and_context()
    url = f"/api/v1/estudiantes/{loan.prestatario_usuario_id}/reputacion"
    assert client.get(url).status_code == 401
    assert client.get(url, headers={"Authorization": "Bearer invalid"}).status_code == 401


def test_request_rejects_client_controlled_identity_and_bad_score() -> None:
    client, _, loan = client_and_context()
    headers = {"Authorization": "Bearer valid"}
    manipulated = client.post(
        f"/api/v1/prestamos/{loan.prestamo_id}/calificaciones",
        json={"puntaje": 5, "evaluado_usuario_id": str(uuid4())},
        headers=headers,
    )
    assert manipulated.status_code == 422
    decimal = client.post(
        f"/api/v1/prestamos/{loan.prestamo_id}/calificaciones",
        json={"puntaje": 4.5},
        headers=headers,
    )
    assert decimal.status_code == 422


def test_openapi_documents_firebase_bearer_and_exact_paths() -> None:
    client, _, _ = client_and_context()
    schema = client.get("/openapi.json").json()
    assert schema["components"]["securitySchemes"]["FirebaseBearer"]["scheme"] == "bearer"
    assert "/api/v1/prestamos/{id}/calificaciones" in schema["paths"]
    assert "/api/v1/estudiantes/{id}/reputacion" in schema["paths"]
