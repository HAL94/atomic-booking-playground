from typing import ClassVar
from uuid import UUID

from pydantic import Field, field_validator

from app.domain.base import BaseDomain
from app.domain.cart_status import CartStatus
from app.models import Cart, CartItem


class CartBase(BaseDomain[Cart]):
    model: ClassVar[Cart] = Cart

    id: UUID | str | None = Field(default=None)
    status: CartStatus
    customer_id: UUID | str
    total: float = Field(default=0)
    cart_items: list["CartItemBase"] | None = Field(default=None)

    @field_validator("total", mode="before")
    @classmethod
    def transform_total(cls, v: float):
        if not v:
            return 0.0
        return round(v, 2)

class CartItemBase(BaseDomain[CartItem]):
    model: ClassVar = CartItem

    id: UUID | str | None = Field(default=None)
    cart_id: UUID | str | None = Field(default=None)
    product_id: UUID | str
    customer_id: UUID | str
    quantity: int
    unit_price_cents: int
