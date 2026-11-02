import signal

from lendup_reputation.config.logging import configure_logging
from lendup_reputation.config.settings import get_settings
from lendup_reputation.infrastructure.messaging.consumer import RabbitMqLoanConsumer
from lendup_reputation.infrastructure.messaging.inbox import LoanProjectionConsumer
from lendup_reputation.infrastructure.persistence.database import (
    create_database_engine,
    create_session_factory,
)


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    if not settings.loan_subscription_enabled:
        raise RuntimeError("LOAN_SUBSCRIPTION_ENABLED debe ser true para iniciar este worker")
    settings.validate_worker_configuration("consumer")
    engine = create_database_engine(settings)
    consumer = RabbitMqLoanConsumer(
        settings, LoanProjectionConsumer(create_session_factory(engine))
    )

    def stop(_signum: int, _frame: object) -> None:
        consumer.stop()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        consumer.run_forever()
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
