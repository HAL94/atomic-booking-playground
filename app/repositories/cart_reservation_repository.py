import logging
from datetime import datetime
from typing import ClassVar

from sqlalchemy import insert, select

from app.core.exceptions import NotFoundException
from app.domain.cart_reservation import CartReservationBase
from app.domain.cart_status import CartReservationStatus
from app.models import CartReservation
from app.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class CartReservationRepository(BaseRepository[CartReservationBase, CartReservation]):
    __model__: ClassVar[CartReservation] = CartReservation

    def __init__(self, session):
        super().__init__(session)

    def domain_model(self, data, as_domain=None):
        if as_domain:
            return as_domain.model_validate(data, from_attributes=True)
        return CartReservationBase.model_validate(data, from_attributes=True)

    async def get_pending_reservation(
        self, user_id: str, cart_id: str, raise_not_found: bool = False
    ) -> CartReservation | None:
        stmt = select(CartReservation).where(
            CartReservation.user_id == user_id,
            CartReservation.cart_id == cart_id,
            CartReservation.status == CartReservationStatus.PENDING,
        )
        reservation = await self.session.scalar(stmt)
        if not reservation and raise_not_found:
            raise NotFoundException(f"Could not find reservation for customer_id {user_id}")
        return reservation

    async def create_reservation(self, user_id: str, cart_id: str, expiration: datetime) -> CartReservationBase:
        cart_res_base = CartReservationBase(
            user_id=user_id, expires_at=expiration, cart_id=cart_id, status=CartReservationStatus.PENDING
        )
        stmt = insert(CartReservation).values(**cart_res_base.model_dump(exclude_none=True)).returning(CartReservation)
        reservation = await self.session.scalar(stmt)
        return self.domain_model(reservation)

    async def expire_cart_reservation(self, cart_id: str, user_id: str) -> CartReservation | None:
        cart_res = await self.get_pending_reservation(user_id, cart_id)
        if not cart_res:
            return None
        cart_res.status = CartReservationStatus.EXPIRED
        return cart_res
