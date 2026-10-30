import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import OutboxEvent, Payment, PaymentStatus
from app.schemas import PaymentAccepted, PaymentCreate, PaymentRead
from app.security import require_api_key

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/payments", tags=["payments"], dependencies=[Depends(require_api_key)])


@router.post("", response_model=PaymentAccepted, status_code=status.HTTP_202_ACCEPTED)
async def create_payment(
    body: PaymentCreate,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=255),
    session: AsyncSession = Depends(get_session),
) -> PaymentAccepted:
    existing = await session.scalar(select(Payment).where(Payment.idempotency_key == idempotency_key))
    if existing:
        return PaymentAccepted(payment_id=existing.id, status=existing.status.value, created_at=existing.created_at)

    payment = Payment(
        amount=body.amount,
        currency=body.currency,
        description=body.description,
        metadata_json=body.metadata,
        status=PaymentStatus.pending,
        idempotency_key=idempotency_key,
        webhook_url=str(body.webhook_url),
    )
    session.add(payment)
    try:
        await session.flush()
        session.add(OutboxEvent(
            event_type="payment.created",
            aggregate_id=payment.id,
            payload={"payment_id": str(payment.id)},
        ))
        await session.commit()
        await session.refresh(payment)
    except IntegrityError:
        await session.rollback()
        existing = await session.scalar(select(Payment).where(Payment.idempotency_key == idempotency_key))
        if existing:
            return PaymentAccepted(payment_id=existing.id, status=existing.status.value, created_at=existing.created_at)
        raise HTTPException(status_code=409, detail="Could not create payment due to a conflict")
    except Exception:
        await session.rollback()
        logger.exception("Failed to create payment")
        raise HTTPException(status_code=500, detail="Failed to create payment")
    return PaymentAccepted(payment_id=payment.id, status=payment.status.value, created_at=payment.created_at)


@router.get("/{payment_id}", response_model=PaymentRead)
async def get_payment(payment_id: UUID, session: AsyncSession = Depends(get_session)) -> PaymentRead:
    payment = await session.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    return PaymentRead.model_validate(payment)
