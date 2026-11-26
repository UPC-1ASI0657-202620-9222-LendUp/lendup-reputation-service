# Contratos de integración

## CONFIRMADO

### Frontend / API Gateway

El repositorio local `lendup-frontend-web` confirma rutas relativas al Gateway:

- `POST /prestamos/{id}/calificaciones` con `{puntaje, comentario}`.
- `GET /estudiantes/{id}/reputacion`.

El servicio expone las rutas completas bajo `/api/v1`. Los campos JSON están en snake_case y
coinciden con `services/reputation.service.ts` y `mapRating`.

### Identidad existente

El backend local confirma `GET /api/v1/estudiantes/me`, protegido por Firebase, y que `usuario.id`
es el UUID interno asociado a `firebase_uid`. El adaptador reenvía el mismo Bearer, exige UUID
válido y, si la respuesta incluye `firebase_uid`, comprueba coincidencia. Ausencia, error o timeout
fallan cerrados (403/503). No se inventó un endpoint nuevo.

## Mensajería integrada y esquema interno

### Esquema canónico interno `PrestamoFinalizado.v1`

Fixture: `contracts/fixtures/prestamo-finalizado.v1.json`. Campos: `event_id`, `event_type`,
`event_version`, `prestamo_id`, `prestamista_usuario_id`, `prestatario_usuario_id`, `finalizado_en`,
`correlation_id`, `aggregate_version`. Es un esquema interno estricto para la capa de adaptación,
no una afirmación sobre el payload externo de Préstamos.

### Evento saliente `CalificacionRegistrada.v1`

Fixture: `contracts/fixtures/calificacion-registrada.v1.json`. Incluye identificadores de evento,
evaluación, préstamo, evaluador/evaluado, puntaje y fecha. La entrega es al menos una vez; consumidores
deduplican por `event_id`.

El entorno E2E verificó el exchange `lendup.domain.events`, la entrada
`loans.loan-finalized.v1` y la salida `reputation.rating-registered.v1`. La cola del consumidor
es `lendup.reputation.loan-finalized.v1`. El adaptador transforma el evento de Préstamos para el
esquema canónico interno.

Los eventos sin versión no reemplazan una proyección existente; una versión menor o igual tampoco.
Solo el tipo estricto `PrestamoFinalizado` habilita evaluación: cancelación, fechas o estados del
navegador no son señales válidas.

## PENDIENTE DE VALIDACIÓN

- Ownership de colas, retención, permisos RabbitMQ y políticas de DLQ en el despliegue.
- URL final de Identidad/Gateway y disponibilidad del campo `firebase_uid` en producción.
- Rutas y políticas del API Gateway, CORS y propagación de correlation ID.
- Política final para enriquecer autores públicos y condición universitaria. Reputación devuelve IDs
  y no replica PII; Identidad sigue siendo propietaria de esos datos.

Fuera de un entorno integrado, los flags son falsos por defecto. El perfil Compose
`messaging` activa cada flag en su worker.

Los hallazgos de compatibilidad de UI están en `docs/frontend-handoff.md`.
