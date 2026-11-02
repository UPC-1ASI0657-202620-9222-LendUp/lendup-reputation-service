import uvicorn

from lendup_reputation.config.settings import get_settings


def main() -> None:
    settings = get_settings()
    forwarded_allow_ips = ",".join(settings.trusted_proxy_ips) or "127.0.0.1"
    uvicorn.run(
        "lendup_reputation.main:app",
        host=settings.api_host,
        port=settings.api_port,
        proxy_headers=settings.proxy_headers_enabled,
        forwarded_allow_ips=forwarded_allow_ips,
    )


if __name__ == "__main__":
    main()
