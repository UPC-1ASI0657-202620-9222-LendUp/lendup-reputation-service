import pytest
from pydantic import ValidationError

from lendup_reputation.config.settings import Settings
from lendup_reputation.main import create_app


def production_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "environment": "production",
        "database_url": "mysql+pymysql://user:secret@mysql/reputation?charset=utf8mb4",
        "database_ssl_ca": "/run/secrets/rds-ca.pem",
        "rabbitmq_url": "amqps://user:secret@rabbitmq/%2F",
        "identity_base_url": "https://identity.internal",
        "cors_origins": ["https://app.lendup.example"],
    }
    values.update(overrides)
    return Settings(**values)


def test_production_disables_docs_and_proxy_headers_by_default() -> None:
    settings = production_settings()
    assert settings.docs_enabled is False
    assert settings.proxy_headers_enabled is False
    app = create_app(settings)
    assert app.docs_url is None
    assert app.openapi_url is None
    app.state.engine.dispose()


@pytest.mark.parametrize(
    "override",
    [
        {"identity_base_url": "http://identity.internal"},
        {"rabbitmq_url": "amqp://user:secret@rabbitmq/%2F"},
        {"database_ssl_ca": None},
        {"cors_origins": ["*"]},
        {"proxy_headers_enabled": True, "trusted_proxy_ips": ["*"]},
    ],
)
def test_production_rejects_insecure_or_incomplete_configuration(
    override: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        production_settings(**override)


def test_production_accepts_explicit_trusted_proxies_and_docs_opt_in() -> None:
    settings = production_settings(
        proxy_headers_enabled=True,
        trusted_proxy_ips=["10.0.0.10", "10.0.0.11"],
        docs_enabled=True,
    )
    assert settings.docs_enabled is True
    assert settings.trusted_proxy_ips == ["10.0.0.10", "10.0.0.11"]
