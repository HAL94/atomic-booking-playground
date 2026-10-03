import logging

from fastapi import HTTPException

from app.repositories.cart_repository import CartRepository
from app.services.base import BaseService
from app.services.inventory_reservation import InventoryReservationService

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class CheckoutService(BaseService):
    def __init__(self, session):
        super().__init__(session)
        self._inv_service = InventoryReservationService(session)
        self._cart_repo = CartRepository(session)

    async def create_cart_reservation(self, user_id: str):
        """
        Let's create a cart reservation
        """
        cart = await self._cart_repo.get_active_cart(user_id)
        if len(cart.cart_items) == 0:
            raise HTTPException(status_code=400, detail="Cannot checkout an empty cart")

        await self._inv_service.reserve_inventory(cart.id, user_id, cart.cart_items)
        await self.session.commit()
        return
