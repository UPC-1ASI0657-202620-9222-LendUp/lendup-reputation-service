# Handoff AWS

Este documento describe requisitos, no inventa recursos ni credenciales AWS.

| Elemento | Valor/acción |
|---|---|
| Puerto | TCP 8082 |
| Imagen propuesta | `fabriciofabianquispebarzola/lendup-reputation-service:<release-tag>` |
| Plataforma | `linux/amd64` |
| API command | `python -m lendup_reputation.server` |
| Consumer | `python -m lendup_reputation.workers.loan_consumer` |
| Outbox | `python -m lendup_reputation.workers.outbox_publisher` |
| Migración | `alembic upgrade head` como job previo y único |
| Liveness | `/health/live` |
| Readiness | `/health/ready` |
| Gateway routes | `/api/v1/prestamos/*/calificaciones`, `/api/v1/estudiantes/*/reputacion` |

## Variables y secretos

No secretas: `ENVIRONMENT`, `API_PORT`, `LOG_LEVEL`, `FIREBASE_PROJECT_ID`,
`FIREBASE_CHECK_REVOKED`, `REQUIRE_VERIFIED_EMAIL`, `IDENTITY_BASE_URL`, `IDENTITY_ME_PATH`,
timeouts, nombres RabbitMQ, flags de workers, `CORS_ORIGINS`, `DOCS_ENABLED`.
También `PROXY_HEADERS_ENABLED`, `TRUSTED_PROXY_IPS` y parámetros de retry/reconexión.

Secretas: `DATABASE_URL`, `RABBITMQ_URL` y credenciales Firebase ADC/workload identity. MySQL exige
CA montado y `DATABASE_SSL_CA`; RabbitMQ exige `amqps://`. Deben venir de
un gestor de secretos o rol de workload; nunca de la imagen, repositorio o logs.

## Dependencias

- MySQL 8.4 propio, charset utf8mb4, backups, cifrado y migración previa.
- RabbitMQ durable con permisos mínimos, TLS, exchange/colas/DLQ validados y monitoreo de profundidad.
- Identidad disponible vía HTTPS para resolución `/api/v1/estudiantes/me`.
- Firebase proyecto `lendup-3cb42` mediante ADC/workload identity.
- Tres workloads desplegables independientemente: API, consumer y publisher.

## Pendiente antes de producción

Validar contrato Préstamos, topología RabbitMQ, URLs Gateway/Identidad, política Swagger, orígenes
CORS, recursos/autoescalado, observabilidad central, alarmas DLQ/Outbox, rotación de secretos y plan
de rollback. No se ha creado release ni publicado Docker Hub.
