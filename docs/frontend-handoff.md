# Handoff de integración frontend

Verificación realizada en modo lectura sobre `lendup-frontend-web`.

## Contratos que deben permanecer estables

- `GET /api/v1/estudiantes/{id}/reputacion`.
- `POST /api/v1/prestamos/{id}/calificaciones` con `puntaje` y `comentario`.
- La respuesta conserva `id`, `prestamo_id`, `evaluador_usuario_id`,
  `evaluado_usuario_id`, `puntaje`, `comentario` y `registrada_en`.

## Hallazgos para el equipo frontend

1. `services/api/mappers/domain.ts` traduce `CANCELADO` a `COMPLETED`. Esto puede mostrar la acción
   de calificar para una operación cancelada. Reputación no la habilita: solo acepta préstamos cuya
   proyección proviene de un evento autoritativo `PrestamoFinalizado`.
2. `mapLoan` inicializa `ratedBy: []`. El estado de préstamos no incorpora quién ya calificó, por lo
   que la UI no puede derivar de ese DTO si debe ocultar la acción. Un POST duplicado recibe 409.
3. Las consultas de reputación cargan autores solo para usuarios presentes en `relatedUserIds`.
   Autores históricos fuera de ese conjunto pueden aparecer sin nombre resuelto. Identidad sigue
   siendo propietaria del nombre público y la verificación universitaria.
4. `http-client.ts` espera errores planos (`error`, `message`, `fieldErrors`), mientras este servicio
   responde `{ "error": { "code", "message", "correlation_id" } }`. El status HTTP sí se mapea,
   pero `serverCode` y el mensaje detallado pueden perderse. Debe acordarse un envelope común en el
   Gateway o ajustarse el cliente en una tarea del frontend.

No se modificó el frontend en esta preparación.
