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

## PROPUESTO

### Esquema canónico interno `PrestamoFinalizado.v1`

Fixture: `contracts/fixtures/prestamo-finalizado.v1.json`. Campos: `event_id`, `event_type`,
`event_version`, `prestamo_id`, `prestamista_usuario_id`, `prestatario_usuario_id`, `finalizado_en`,
`correlation_id`, `aggregate_version`. Es un esquema interno estricto para la capa de adaptación,
no una afirmación sobre el payload externo de Préstamos.

### Evento saliente `CalificacionRegistrada.v1`

Fixture: `contracts/fixtures/calificacion-registrada.v1.json`. Incluye identificadores de evento,
evaluación, préstamo, evaluador/evaluado, puntaje y fecha. La entrega es al menos una vez; consumidores
deduplican por `event_id`.

Los nombres locales de exchange, colas y routing keys del `.env.example` son propuestas operativas,
no contratos definitivos.

Los eventos sin versión no reemplazan una proyección existente; una versión menor o igual tampoco.
Solo el tipo estricto `PrestamoFinalizado` habilita evaluación: cancelación, fechas o estados del
navegador no son señales válidas.

## PENDIENTE DE VALIDACIÓN

- Payload, tipo, versión y ordenamiento emitidos realmente por Préstamos.
- Exchange, routing keys, ownership de colas, DLQ, retención y permisos RabbitMQ.
- URL final de Identidad/Gateway y disponibilidad del campo `firebase_uid` en producción.
- Rutas y políticas del API Gateway, CORS y propagación de correlation ID.
- Política final para enriquecer autores públicos y condición universitaria. Reputación devuelve IDs
  y no replica PII; Identidad sigue siendo propietaria de esos datos.

Hasta cerrar estos puntos, `LOAN_SUBSCRIPTION_ENABLED=false` y
`OUTBOX_PUBLISHER_ENABLED=false` son los valores seguros por defecto.

Los hallazgos de compatibilidad de UI están en `docs/frontend-handoff.md`.
