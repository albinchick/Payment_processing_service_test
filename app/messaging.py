import json
import logging
from datetime import datetime, timezone
from typing import Any

from faststream import FastStream
from faststream.rabbit import RabbitBroker, RabbitExchange, RabbitQueue
from sqlalchemy import select

from app.core.config import settings
from app.db import SessionFactory
from app.models import OutboxEvent

logger = logging.getLogger(__name__)
exchange = RabbitExchange(settings.payment_exchange, type="direct", durable=True)
dead_exchange = RabbitExchange(settings.dlx_exchange, type="direct", durable=True)
payment_queue = RabbitQueue(
    settings.payment_queue,
    durable=True,
    routing_key=settings.payment_routing_key,
    arguments={"x-dead-letter-exchange": settings.dlx_exchange, "x-dead-letter-routing-key": settings.dlq_queue},
)
dlq = RabbitQueue(settings.dlq_queue, durable=True, routing_key=settings.dlq_queue)

broker = RabbitBroker(settings.rabbitmq_url)
app = FastStream(broker)


async def publish_outbox_forever() -> None:
    """Poll committed outbox rows and publish; rows are marked only after broker publish succeeds."""
    import asyncio

    while True:
        try:
            async with SessionFactory() as session:
                rows = (await session.scalars(
                    select(OutboxEvent)
                    .where(OutboxEvent.published_at.is_(None))
                    .order_by(OutboxEvent.created_at)
                    .limit(settings.outbox_batch_size)
                )).all()
                for row in rows:
                    try:
                        await broker.publish(
                            row.payload,
                            exchange=exchange,
                            routing_key=settings.payment_routing_key,
                            message_id=str(row.id),
                            headers={"event_type": row.event_type},
                        )
                        row.published_at = datetime.now(timezone.utc)
                        row.attempts += 1
                        row.last_error = None
                        await session.commit()
                    except Exception as exc:
                        row.attempts += 1
                        row.last_error = str(exc)[:2000]
                        await session.commit()
                        logger.exception("Outbox publish failed for %s", row.id)
                        break
        except Exception:
            logger.exception("Outbox polling cycle failed")
        await asyncio.sleep(settings.outbox_poll_interval)


@broker.subscriber(payment_queue)
async def process_payment_event(message: dict[str, Any]) -> None:
    # The payment processor is registered by consumer.py to keep the consumer entry point explicit.
    from app.worker import handle_payment_message
    await handle_payment_message(message)
