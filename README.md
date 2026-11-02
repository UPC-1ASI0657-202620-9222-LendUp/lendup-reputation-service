# LendUp Reputation Service

Microservicio FastAPI de reputación y calificaciones de LendUp. Implementa RF34, RF35, US29 y
US30 con arquitectura hexagonal, MySQL por servicio, consumidor idempotente y Transactional
Outbox para RabbitMQ.

## Estado

Los contratos HTTP con el frontend y el endpoint de resolución de
Identidad fueron comprobados contra los repositorios locales. La integración productiva con
Préstamos, RabbitMQ, API Gateway e Identidad permanece pendiente de configuración/validación
externa; por eso la suscripción RabbitMQ está desactivada por defecto y las operaciones protegidas
fallan cerradas si Identidad no está disponible.

## API

- `POST /api/v1/prestamos/{id}/calificaciones` — requiere Bearer Firebase y préstamo finalizado
  presente en la proyección local.
- `GET /api/v1/estudiantes/{id}/reputacion` — promedio, cantidad y calificaciones.
- `GET /health/live` y `GET /health/ready` — liveness y readiness.
- `/docs` y `/openapi.json` — habilitados por configuración.

El cuerpo del POST solo acepta `puntaje` y `comentario`; nunca acepta la identidad del evaluador o
evaluado. El frontend limita comentarios a 400 caracteres y el servicio adopta ese máximo como
política defensiva compatible, no como requisito original del informe.

## Ejecución local

Requisitos: Python 3.12, uv, Docker Desktop y Docker Compose.

```powershell
Copy-Item .env.example .env
# Configure IDENTITY_BASE_URL y credenciales externas/ADC según el entorno.
uv sync --all-groups --frozen
docker compose up -d --build mysql rabbitmq migrate api
docker compose ps
```

La API queda en `http://localhost:8082`; MySQL en `localhost:3307` y RabbitMQ Management en
`http://localhost:15673`. Los workers se inician solo al habilitar el perfil de mensajería:

```powershell
docker compose --profile messaging up -d loan-consumer outbox-publisher
```

Los nombres de exchange/routing key del `.env.example` son provisionales. No habilite mensajería
en producción hasta validarlos con el servicio de Préstamos.

## Desarrollo y migraciones

```powershell
uv run alembic upgrade head
uv run uvicorn lendup_reputation.main:app --reload --port 8082
uv run ruff check .
uv run mypy src
uv run pytest -m "not integration" -q
$env:RUN_INTEGRATION = "1"; uv run pytest -m integration -q
docker compose config
docker build --platform linux/amd64 -t lendup-reputation-service:local .
```

Alembic es el único mecanismo de esquema productivo; el servicio no llama
`Base.metadata.create_all()`.

## Seguridad

Firebase Admin valida firma, proyecto/audiencia, emisor, vigencia y revocación. El correo debe estar
verificado. El Firebase UID se resuelve al UUID interno mediante el contrato confirmado
`GET /api/v1/estudiantes/me`; no se usa el UID como UUID ni se aceptan cabeceras de identidad.
ADC o secretos montados se proporcionan en runtime y nunca se incluyen en la imagen.

## Documentación

- [Arquitectura](docs/architecture.md)
- [Cumplimiento C4](docs/c4-compliance.md)
- [Reglas de negocio](docs/business-rules.md)
- [Contratos de integración](docs/integration-contracts.md)
- [Pruebas](docs/testing.md)
- [Handoff AWS](docs/aws-handoff.md)
- [Entrega a DevOps](docs/devops-handoff.md)
- [Handoff frontend](docs/frontend-handoff.md)
