from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    environment: Literal["development", "test", "production"] = "development"
    app_name: str = "LendUp Reputation Service"
    api_host: str = "0.0.0.0"
    api_port: int = 8082
    log_level: str = "INFO"
    database_url: SecretStr = SecretStr(
        "mysql+pymysql://lendup:lendup@localhost:3307/lendup_reputacion?charset=utf8mb4"
    )
    database_ssl_ca: str | None = None
    firebase_project_id: str = Field(min_length=1)
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
    rabbitmq_retry_queue: str | None = None
    loan_subscription_enabled: bool = False
    outbox_publisher_enabled: bool = False
    consumer_max_retries: int = Field(default=5, ge=0, le=20)
    consumer_retry_base_ms: int = Field(default=1000, ge=100, le=60000)
    consumer_retry_max_ms: int = Field(default=60000, ge=1000, le=600000)
    consumer_reconnect_max_seconds: float = Field(default=30.0, ge=1.0, le=300.0)
    outbox_batch_size: int = Field(default=50, ge=1, le=500)
    outbox_poll_seconds: float = Field(default=2.0, ge=0.1)
    cors_origins: list[str] = []
    docs_enabled: bool | None = None
    proxy_headers_enabled: bool = False
    trusted_proxy_ips: list[str] = []

    @field_validator("identity_me_path")
    @classmethod
    def validate_identity_path(cls, value: str) -> str:
        if value != "/api/v1/estudiantes/me":
            raise ValueError("identity_me_path must use the confirmed Identity contract")
        return value

    @field_validator("firebase_project_id")
    @classmethod
    def validate_firebase_project_id(cls, value: str) -> str:
        if value != "lendup-desarrollo":
            raise ValueError("FIREBASE_PROJECT_ID must be lendup-desarrollo")
        return value

    @model_validator(mode="after")
    def secure_environment_defaults(self) -> "Settings":
        if self.docs_enabled is None:
            self.docs_enabled = self.environment != "production"
        if self.consumer_retry_max_ms < self.consumer_retry_base_ms:
            raise ValueError("consumer_retry_max_ms must be >= consumer_retry_base_ms")
        if self.environment != "production":
            return self
        problems: list[str] = []
        database_url = self.database_url.get_secret_value()
        rabbitmq_url = self.rabbitmq_url.get_secret_value()
        if "lendup:lendup@localhost" in database_url:
            problems.append("DATABASE_URL")
        if not self.database_ssl_ca:
            problems.append("DATABASE_SSL_CA")
        if rabbitmq_url.startswith("amqp://"):
            problems.append("RABBITMQ_URL must use amqps://")
        if self.identity_base_url is None or self.identity_base_url.scheme != "https":
            problems.append("IDENTITY_BASE_URL must use https://")
        if not self.firebase_project_id:
            problems.append("FIREBASE_PROJECT_ID")
        if "*" in self.cors_origins:
            problems.append("CORS_ORIGINS cannot contain *")
        if self.proxy_headers_enabled and (
            not self.trusted_proxy_ips or "*" in self.trusted_proxy_ips
        ):
            problems.append("TRUSTED_PROXY_IPS must be explicit when proxy headers are enabled")
        if problems:
            raise ValueError("Configuración production inválida: " + ", ".join(problems))
        return self

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
