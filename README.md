
# LendUp Reputation Service

Microservicio de Reputación y Calificaciones de LendUp.

## Tecnologías

- Python 3.12
- FastAPI
- MySQL
- RabbitMQ
- SQLAlchemy
- Alembic
- Docker

## Arquitectura

Domain-Driven Design (DDD) y arquitectura hexagonal, conforme al diseño de componentes C4 de LendUp.

## Funcionalidades

- RF34: Consulta de reputación.
- RF35: Calificación posterior a un préstamo finalizado.
- US29: Consultar reputación de un estudiante.
- US30: Calificar la experiencia de préstamo.

## Estado

Proyecto en preparación arquitectónica.

Los contratos de integración con Préstamos e Identidad deben verificarse antes de implementar los adaptadores definitivos.
  