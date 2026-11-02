from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    environment: Literal["development", "test", "production"] = "development"
    app_name: str = "LendUp Reputation Service"
    api_port: int = 8082
    log_level: str = "INFO"
    database_url: SecretStr = SecretStr(
        "mysql+pymysql://lendup:lendup@localhost:3307/lendup_reputacion?charset=utf8mb4"
    )
    firebase_project_id: str = "lendup-3cb42"
    firebase_check_revoked: bool = True
    require_verified_email: bool = True
    identity_base_url: AnyHttpUrl | None = None
    identity_me_path: str = "/api/v1/estudiantes/me"
    identity_timeout_seconds: float = 3.0
    rabbitmq_url: SecretStr = SecretStr("amqp://guest:guest@localhost:5673/%2F")
    rabbitmq_exchange: str | None = None
    rabbitmq_loan_queue: str | None = None
    rabbitmq_loan_routing_key: str | None = None
    rabbitmq_rating_routing_key: str | None = None
    rabbitmq_dlq: str | None = None
    loan_subscription_enabled: bool = False
    outbox_publisher_enabled: bool = False
    outbox_batch_size: int = Field(default=50, ge=1, le=500)
    outbox_poll_seconds: float = Field(default=2.0, ge=0.1)
    cors_origins: list[str] = []
    docs_enabled: bool = True

    @field_validator("identity_me_path")
    @classmethod
    def validate_identity_path(cls, value: str) -> str:
        if value != "/api/v1/estudiantes/me":
            raise ValueError("identity_me_path must use the confirmed Identity contract")
        return value

    def validate_worker_configuration(self, worker: Literal["consumer", "outbox"]) -> None:
        required = {
            "consumer": {
                "rabbitmq_exchange": self.rabbitmq_exchange,
                "rabbitmq_loan_queue": self.rabbitmq_loan_queue,
                "rabbitmq_loan_routing_key": self.rabbitmq_loan_routing_key,
                "rabbitmq_dlq": self.rabbitmq_dlq,
            },
            "outbox": {
                "rabbitmq_exchange": self.rabbitmq_exchange,
                "rabbitmq_rating_routing_key": self.rabbitmq_rating_routing_key,
            },
        }[worker]
        missing = [key for key, value in required.items() if not value]
        if missing:
            raise RuntimeError(
                f"Configuración RabbitMQ pendiente de validación: {', '.join(sorted(missing))}"
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
