from datetime import datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, Field


class OrderStatus(StrEnum):
    pending = "pending"
    paid = "paid"
    shipped = "shipped"
    cancelled = "cancelled"


class OrderItem(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)


class Order(BaseModel):
    id: int
    customer_id: int
    items: list[OrderItem]
    total: float
    status: OrderStatus = OrderStatus.pending
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class OrderCreate(BaseModel):
    customer_id: int
    items: list[OrderItem]

