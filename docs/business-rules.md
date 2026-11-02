# Reglas de negocio

- El puntaje es entero estricto de 1 a 5; booleanos, decimales y strings se rechazan.
- El comentario es opcional, se recorta en extremos y el vacío se almacena como `null`.
- Se adopta máximo de 400 caracteres por compatibilidad defensiva con el frontend. No proviene del
  requisito funcional oficial y requiere decisión del Product Owner si se desea cambiar.
- Solo una proyección proveniente de `PrestamoFinalizado` habilita calificar.
- Solo prestamista y prestatario pueden evaluar, siempre a la contraparte determinada por la
  proyección. No existe campo cliente para elegir evaluado.
- No se permite autoevaluación ni más de una evaluación por participante/préstamo.
- Ambos participantes pueden evaluar de manera independiente.
- La unicidad se valida en dominio y se impone definitivamente en MySQL.
- Sin calificaciones: cantidad `0`, promedio `0.0`, lista vacía.
- El promedio se redondea half-up a una cifra y las calificaciones se ordenan por fecha/UUID
  descendente para resultados deterministas.
- No se implementan edición, eliminación ni moderación automática.
