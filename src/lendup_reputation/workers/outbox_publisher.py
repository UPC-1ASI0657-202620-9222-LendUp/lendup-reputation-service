import logging
import signal
import time

from lendup_reputation.config.logging import configure_logging
from lendup_reputation.config.settings import get_settings
from lendup_reputation.infrastructure.messaging.outbox import MessageBrokerAdapter, OutboxPublisher
from lendup_reputation.infrastructure.persistence.database import (
    create_database_engine,
    create_session_factory,
)


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = logging.getLogger(__name__)
    if not settings.outbox_publisher_enabled:
        raise RuntimeError("OUTBOX_PUBLISHER_ENABLED debe ser true para iniciar este worker")
    settings.validate_worker_configuration("outbox")
    engine = create_database_engine(settings)
    publisher = OutboxPublisher(
        create_session_factory(engine), MessageBrokerAdapter(settings), settings
    )
    running = True

    def stop(_signum: int, _frame: object) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    while running:
        try:
            count = publisher.publish_batch()
            if count:
                logger.info("outbox_batch_published count=%d", count)
        except Exception:
            logger.exception("outbox_batch_failed")
        time.sleep(settings.outbox_poll_seconds)
    engine.dispose()


if __name__ == "__main__":
    main()
