from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from lendup_reputation.application.service import ReputacionApplicationService
from lendup_reputation.config.logging import configure_logging
from lendup_reputation.config.settings import Settings, get_settings
from lendup_reputation.infrastructure.persistence.database import (
    create_database_engine,
    create_session_factory,
)
from lendup_reputation.infrastructure.persistence.repository import SqlAlchemyUnitOfWork
from lendup_reputation.infrastructure.security import FirebaseTokenVerifier, HttpIdentityResolver
from lendup_reputation.interfaces.api.errors import register_error_handlers
from lendup_reputation.interfaces.api.router import router


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or get_settings()
    configure_logging(config.log_level)
    engine = create_database_engine(config)
    factory = create_session_factory(engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        engine.dispose()

    app = FastAPI(
        title=config.app_name,
        version="0.1.0",
        description="RF34/RF35 - reputación y calificaciones de LendUp",
        docs_url="/docs" if config.docs_enabled else None,
        redoc_url="/redoc" if config.docs_enabled else None,
        openapi_url="/openapi.json" if config.docs_enabled else None,
        lifespan=lifespan,
    )
    app.state.settings = config
    app.state.engine = engine
    app.state.session_factory = factory
    app.state.application_service = ReputacionApplicationService(
        lambda: SqlAlchemyUnitOfWork(factory)
    )
    app.state.token_verifier = FirebaseTokenVerifier(config)
    app.state.identity_resolver = HttpIdentityResolver(config)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Correlation-ID"],
    )

    @app.middleware("http")
    async def correlation_id(request: Request, call_next: object) -> JSONResponse:
        request.state.correlation_id = request.headers.get("X-Correlation-ID", str(uuid4()))
        response = await call_next(request)  # type: ignore[operator]
        response.headers["X-Correlation-ID"] = request.state.correlation_id
        return response  # type: ignore[no-any-return]

    @app.get("/health/live", tags=["Health"], include_in_schema=False)
    def liveness() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready", tags=["Health"], include_in_schema=False)
    def readiness() -> JSONResponse:
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return JSONResponse({"status": "ready"})
        except Exception:
            return JSONResponse({"status": "not_ready"}, status_code=503)

    app.include_router(router)
    register_error_handlers(app)
    return app


app = create_app()
