import asyncio
import logging
import random
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db import SessionFactory
from app.models import Payment, PaymentStatus

logger = logging.getLogger(__name__)


async def _send_webhook(payment: Payment, attempts: int = 3) -> None:
    payload = {
        "payment_id": str(payment.id),
        "status": payment.status.value,
        "amount": str(payment.amount),
        "currency": payment.currency,
        "processed_at": payment.processed_at.isoformat() if payment.processed_at else None,
    }
    async with httpx.AsyncClient(timeout=settings.webhook_timeout_seconds) as client:
        for attempt in range(attempts):
            try:
                response = await client.post(payment.webhook_url, json=payload)
                response.raise_for_status()
                return
            except (httpx.HTTPError, httpx.TimeoutException) as exc:
                logger.warning("Webhook attempt %s/%s failed for payment %s: %s", attempt + 1, attempts, payment.id, exc)
                if attempt + 1 < attempts:
                    await asyncio.sleep(2 ** attempt)
    logger.error("Webhook delivery exhausted for payment %s", payment.id)


async def handle_payment_message(message: dict[str, Any]) -> None:
    payment_id = UUID(str(message["payment_id"]))
    async with SessionFactory() as session:
        payment = await session.get(Payment, payment_id)
        if payment is None:
            logger.error("Payment %s referenced by message does not exist", payment_id)
            return
        # Idempotent consumer: a redelivered event must not process an already-final payment again.
        if payment.status != PaymentStatus.pending:
            return

        await asyncio.sleep(random.uniform(2, 5))
        payment.status = PaymentStatus.succeeded if random.random() < 0.9 else PaymentStatus.failed
        payment.processed_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(payment)
        await _send_webhook(payment)
