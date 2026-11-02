# Changelog

Todos los cambios relevantes siguen Keep a Changelog y versionado semántico.

## [Unreleased]

### Added

- Dominio de evaluaciones, validador y cálculo determinista de reputación.
- API FastAPI compatible con las rutas del frontend y autenticación Firebase fail-closed.
- Resolución externa Firebase UID → UUID interno mediante el contrato de Identidad.
- Persistencia SQLAlchemy/MySQL, migración Alembic inicial y unicidad concurrente.
- Proyección idempotente de préstamos finalizados, Inbox, Outbox y workers RabbitMQ.
- Docker, Compose, análisis estático, pruebas automatizadas y GitHub Actions.
- Documentación operativa, C4, contratos y handoff de despliegue.
