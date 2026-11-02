# Pruebas

## Capas

- Dominio: score, comentario, cálculo, vacío, precisión y orden.
- Aplicación: dos direcciones válidas, tercero, autoevaluación, préstamo desconocido, duplicado y
  artefactos transaccionales.
- Contrato: rutas/campos exactos, OpenAPI Bearer, errores e identidad no manipulable.
- Seguridad: token inválido, expirado, revocado, otro proyecto, correo no verificado, resolución
  ausente y vinculación UID incorrecta.
- Eventos: esquema válido, versión/tipo incompatible y campos desconocidos.
- Arquitectura: fronteras de imports y delegación.
- Integración: migraciones MySQL 8.4, Inbox idempotente/atrasado, restricción concurrente y Outbox;
  RabbitMQ real con entrega persistente confirmada.
- Transporte: ACK posterior a commit, retry durable, límite/DLQ, correlation ID, reconexión y
  topología durable.
- Configuración production: documentación deshabilitada por defecto, TLS externo y proxies
  confiables explícitos.

## Comandos

```powershell
uv sync --all-groups --frozen
uv run ruff check .
uv run mypy src
uv run pytest -m "not integration" --cov=lendup_reputation --cov-report=term-missing -q
$env:RUN_INTEGRATION = "1"
uv run pytest -m integration -q
```

Las pruebas `integration` requieren Docker; si `RUN_INTEGRATION` no vale `1`, pytest reporta el skip
de forma explícita. CI posee un job separado con Testcontainers. En algunos sandboxes Windows,
Starlette TestClient necesita ejecución fuera del aislamiento porque AnyIO crea un socketpair local.
El umbral de cobertura del job rápido mide dominio, aplicación e interfaz HTTP; infraestructura y
workers se verifican en el job Testcontainers separado y se excluyen de ese porcentaje para no
confundir código no ejecutado con cobertura unitaria.

## Diagnóstico

- Migración falla: revisar `DATABASE_URL`, salud de MySQL y `docker compose logs mysql migrate`.
- Readiness 503: ejecutar `alembic current`, revisar credenciales y DNS.
- POST 403: confirmar que Identidad resuelve el UID Firebase al UUID interno.
- Worker no inicia: es esperado si los flags están desactivados o faltan nombres RabbitMQ validados.
- Mensajes en DLQ: inspeccionar payload/versión y `x-lendup-retry`; no reenviar sin corregir causa.
