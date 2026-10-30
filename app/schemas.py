import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


Currency = Literal["RUB", "USD", "EUR"]


class PaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    currency: Currency
    description: str = Field(min_length=1, max_length=500)
    metadata: dict[str, Any] = Field(default_factory=dict)
    webhook_url: HttpUrl


class PaymentAccepted(BaseModel):
    payment_id: uuid.UUID
    status: str
    created_at: datetime


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    payment_id: uuid.UUID = Field(validation_alias="id")
    amount: Decimal
    currency: str
    description: str
    metadata: dict[str, Any] = Field(validation_alias="metadata_json")
    status: str
    webhook_url: str
    created_at: datetime
    processed_at: datetime | None
