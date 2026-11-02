# Cumplimiento C4 — Figura 19

| Componente | Implementación | Responsabilidad real |
|---|---|---|
| ReputacionController | `src/lendup_reputation/interfaces/api/router.py` | Endpoints, DTO y delegación |
| ReputacionApplicationService | `src/lendup_reputation/application/service.py` | Casos de uso, transacción y eventos |
| Evaluacion | `src/lendup_reputation/domain/models.py` | Agregado e invariantes |
| CalificacionValidator | `src/lendup_reputation/domain/services.py` | Participación, contraparte y duplicado |
| ReputationCalculator | `src/lendup_reputation/domain/services.py` | Promedio, cantidad, orden y vacío |
| EvaluacionRepository | `src/lendup_reputation/application/ports.py` | Puerto de persistencia |
| EvaluacionRepositoryImpl | `src/lendup_reputation/infrastructure/persistence/repository.py` | Adaptador SQLAlchemy/MySQL |
| DomainEventPublisher | `src/lendup_reputation/application/ports.py` | Puerto de registro Outbox |
| MessageBrokerAdapter | `src/lendup_reputation/infrastructure/messaging/outbox.py` y `consumer.py` | Publicación confirmada y transporte completo del consumidor |

La denominación `ReputacionCalculator` de la figura corresponde a `ReputationCalculator` en el
texto y en el código. Se conserva el segundo nombre para unificar el lenguaje técnico del informe.

Elementos externos: MySQL, RabbitMQ, API Gateway, Identidad y Préstamos. Ninguno se importa en el
dominio. `tests/architecture/test_boundaries.py` comprueba estas fronteras y que el controlador
delegue la lógica.
