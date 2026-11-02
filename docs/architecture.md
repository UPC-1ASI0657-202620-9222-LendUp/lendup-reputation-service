# Arquitectura

## Decisiones

El código sigue arquitectura hexagonal. `domain` contiene el agregado y reglas puras;
`application` orquesta los casos de uso y define puertos; `infrastructure` adapta MySQL, Firebase,
Identidad y RabbitMQ; `interfaces` contiene FastAPI; `workers` contiene procesos independientes.
Las dependencias apuntan hacia dominio/aplicación y una prueba AST impide imports de frameworks en
el dominio.

El flujo de escritura es:

1. FastAPI valida el Bearer Firebase y obtiene el UID.
2. Identidad resuelve ese UID al UUID interno usando `/api/v1/estudiantes/me`.
3. La aplicación carga la proyección local autoritativa de un préstamo finalizado.
4. `CalificacionValidator` determina la contraparte y verifica participación/duplicado.
5. Evaluación, auditoría y evento Outbox se insertan en una transacción.
6. El publisher independiente envía con delivery persistente y publisher confirms.
7. Solo tras confirmación se marca el Outbox como publicado.

El transporte de entrada vive en
`infrastructure/messaging/consumer.py`: encapsula conexión, topología, suscripción, ACK/NACK,
retry/DLQ y reconexión. El worker solo configura dependencias, señales y ejecuta el adaptador.

El flujo de entrada de Préstamos valida un esquema canónico v1, aplica proyección y
`processed_events` en una transacción, y hace ACK después del commit. Los errores transitorios pasan
por una cola retry con TTL/backoff; tras cinco intentos se envían a DLQ. Eventos inválidos o de
versión incompatible van directamente a DLQ.

Un evento sin `aggregate_version` solo puede crear una proyección inexistente; nunca reemplaza una
proyección previa. Una versión menor o igual también se registra como procesada sin mutar el estado.
Una cancelación o una fecha alcanzada no se interpreta como finalización.

## Consistencia y concurrencia

MySQL impone `UNIQUE(prestamo_id, evaluador_usuario_id)`. La validación anticipada mejora el error,
pero la restricción es la autoridad bajo concurrencia. Un `IntegrityError` se traduce a conflicto
controlado. El Outbox usa `FOR UPDATE SKIP LOCKED`, reclamos con timeout y publicación al menos una
vez. Los consumidores deben deduplicar `CalificacionRegistrada` por `event_id`.

## Precisión

El promedio usa `Decimal`, redondeo `ROUND_HALF_UP` a una cifra decimal y orden descendente por
`(registrada_en, id)`. Sin evaluaciones devuelve `0`, `0.0`, `[]`.

## Datos y privacidad

Reputación almacena UUID públicos, puntaje, comentario y timestamps; no replica nombres, correos ni
datos institucionales privados. La UI puede resolver autores visibles con Identidad usando los IDs
de la respuesta. No hay foreign keys a bases de otros servicios.
