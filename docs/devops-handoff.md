# Entrega a DevOps

## IMPLEMENTADO Y PROBADO

| Elemento | Valor |
|---|---|
| Imagen | `fabriciofabianquispebarzola/lendup-reputation-service:<tag>` |
| Tag de publicación | El Git tag exacto, por ejemplo `v0.1.0`; no se publica `latest` |
| Plataforma / usuario | `linux/amd64` / UID-GID 10001 `lendup` |
| Puerto | `8082` configurable con `API_PORT` |
| API | `python -m lendup_reputation.server` |
| Consumer | `python -m lendup_reputation.workers.loan_consumer` |
| Publisher | `python -m lendup_reputation.workers.outbox_publisher` |
| Migración | `alembic upgrade head`, job único previo a API/workers |
| Liveness | `GET /health/live` |
| Readiness | `GET /health/ready`, comprueba MySQL |

MySQL 8.4 mantiene `evaluaciones`, `prestamos_evaluables`, `outbox_events`, `processed_events` y
`registro_auditoria`. La restricción `UNIQUE(prestamo_id, evaluador_usuario_id)` es la autoridad bajo
concurrencia. API, consumer y publisher son procesos independientes.

## PREPARADO PARA INTEGRAR

### Variables obligatorias de aplicación

- `ENVIRONMENT=production`, `API_HOST`, `API_PORT`, `LOG_LEVEL`.
- `DATABASE_URL` y `DATABASE_SSL_CA`.
- `FIREBASE_PROJECT_ID=lendup-3cb42`, `FIREBASE_CHECK_REVOKED=true`,
  `REQUIRE_VERIFIED_EMAIL=true`.
- `IDENTITY_BASE_URL` HTTPS, `IDENTITY_ME_PATH=/api/v1/estudiantes/me`, timeout.
- `CORS_ORIGINS`, `DOCS_ENABLED=false` salvo habilitación explícita.
- `PROXY_HEADERS_ENABLED`; si es true, `TRUSTED_PROXY_IPS` debe enumerar proxies y no acepta `*`.

### Variables de mensajería

- `RABBITMQ_URL` debe usar `amqps://` en producción.
- `RABBITMQ_EXCHANGE`, `RABBITMQ_LOAN_QUEUE`, `RABBITMQ_LOAN_ROUTING_KEY`.
- `RABBITMQ_RATING_ROUTING_KEY`, `RABBITMQ_DLQ`, `RABBITMQ_RETRY_QUEUE`.
- `CONSUMER_MAX_RETRIES`, `CONSUMER_RETRY_BASE_MS`, `CONSUMER_RETRY_MAX_MS` y
  `CONSUMER_RECONNECT_MAX_SECONDS`.
- `LOAN_SUBSCRIPTION_ENABLED` y `OUTBOX_PUBLISHER_ENABLED`; mantener false hasta validar contrato.

Valores locales propuestos: exchange `lendup.events`, cola
`lendup.reputation.loan-finalized.v1`, routing de entrada `loans.loan-finalized.v1`, routing de salida
`reputation.rating-registered.v1`, retry `.retry` y DLQ `.dlq`. No son valores productivos
confirmados.

### Secretos externos

`DATABASE_URL`, `RABBITMQ_URL`, credenciales Docker Hub y credenciales Firebase mediante
ADC/workload identity. El CA MySQL se monta como archivo y se referencia con `DATABASE_SSL_CA`.
No montar secretos dentro de la imagen ni enviarlos a logs.

### Contratos

- REST: `GET /api/v1/estudiantes/{id}/reputacion` y
  `POST /api/v1/prestamos/{id}/calificaciones`.
- Consume esquema canónico provisional `PrestamoFinalizado.v1`; ACK solo después del commit Inbox.
- Publica `CalificacionRegistrada.v1` mediante Outbox y publisher confirms, entrega al menos una vez.
- `event_id` es la clave de deduplicación y `correlation_id` se preserva.

### Arranque

1. Proveer secretos, CA y variables validadas.
2. Ejecutar `alembic upgrade head` y exigir salida 0.
3. Iniciar API y esperar readiness 200.
4. Iniciar publisher si la topología saliente fue aprobada.
5. Iniciar consumer únicamente cuando Préstamos confirme contrato y topología.
6. Verificar métricas/logs, profundidad de Outbox, retry y DLQ.

### Rollback

Detener primero consumer, luego publisher y API; desplegar la imagen anterior por tag inmutable. No
hacer downgrade automático de Alembic: evaluar compatibilidad y restaurar backup si un cambio de
esquema futuro no es backward-compatible. Los mensajes no confirmados permanecen en RabbitMQ y los
Outbox no publicados permanecen en MySQL.

### Aceptación reproducible

```bash
uv lock --check
uv sync --all-groups --frozen
uv run ruff check .
uv run mypy src
uv run pytest -m "not integration" -q
RUN_INTEGRATION=1 uv run pytest -m integration -q
docker compose config --quiet
docker compose build
docker compose --profile messaging up -d
docker compose --profile messaging ps
curl -f http://localhost:8082/health/ready
```

GitHub Actions requiere `DOCKERHUB_USERNAME` y `DOCKERHUB_TOKEN`. `publish.yml` ejecuta análisis,
unitarias, integración MySQL/RabbitMQ, OpenAPI y build antes de publicar solo el tag de release.

## PENDIENTE DE OTRO EQUIPO

- Préstamos: payload externo, versión, semántica de orden, exchange y routing key definitivos.
- Identidad/Gateway: URL productiva, SLA, envelope HTTP común y resolución de autores históricos.
- DevOps: broker/vhost/permisos, TLS/CA, retención retry/DLQ, alertas, sizing, backups, secretos,
  IPs de proxies confiables y orígenes CORS.
- Frontend: corregir `CANCELADO -> COMPLETED`, `ratedBy`, autores históricos y envelope de errores.
- Seguridad: asignar workload identity Firebase y probar tokens reales del proyecto en el entorno.
