from datetime import datetime
from typing import ClassVar
from uuid import UUID

from pydantic import Field

from app.domain.base import BaseDomain
from app.domain.cart_status import CartReservationStatus
from app.models import CartReservation


class CartReservationBase(BaseDomain[CartReservation]):
    model: ClassVar[CartReservation] = CartReservation

    id: str | UUID | None = Field(default=None)
    user_id: str | UUID
    cart_id: str | UUID
    status: CartReservationStatus
    expires_at: datetime
