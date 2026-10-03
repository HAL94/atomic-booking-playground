import logging
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import Integer, column, select, update, values

from app.models import CartItem, Inventory
from app.repositories.cart_reservation_repository import CartReservationRepository
from app.services.base import BaseService

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class InventoryReservationService(BaseService):
    def __init__(self, session):
        super().__init__(session)
        self._seconds = 60
        self._cart_res_repo = CartReservationRepository(session)

    async def _inventory_values(self, cart_items: list[CartItem]):
        product_ids = {item.product_id for item in cart_items}
        # lock ids
        await self.session.execute(
            select(Inventory.product_id)
            .where(Inventory.product_id.in_(product_ids))
            .order_by(Inventory.product_id)
            .with_for_update()
        )

        # inline-table of values
        inventory_values = values(
            column("product_id", Inventory.product_id.type),
            column("qty", Integer),
            name="inventory_values",
        ).data([(item.product_id, item.quantity) for item in cart_items])

        return inventory_values

    async def reserve_inventory(self, cart_id: str, user_id: str, cart_items: list[CartItem]):
        expiration = datetime.now(tz=timezone.utc) + timedelta(seconds=self._seconds)
        await self._cart_res_repo.create_reservation(user_id, cart_id, expiration)

        inventory_values = await self._inventory_values(cart_items)
        stmt = (
            update(Inventory)
            .where(Inventory.product_id == inventory_values.c.product_id, Inventory.stock >= inventory_values.c.qty)
            .values(stock=Inventory.stock - inventory_values.c.qty)
            .returning(Inventory.product_id)
        )
        result_cursor = await self.session.scalars(stmt)
        updated_products = result_cursor.all()
        if len(updated_products) != len(cart_items):
            raise HTTPException(status_code=400, detail="Insufficient stock in one or more items in your cart")

    async def release_inventory(self, cart_id: str, user_id: str, cart_items: list[CartItem]):
        reservation = await self._cart_res_repo.expire_cart_reservation(cart_id, user_id)
        if not reservation:
            logger.debug(f"[InventoryReservationService]: no reservation found for {cart_id}. Skipping..")
            return
        if len(cart_items) <= 0:
            logger.debug(f"[InventoryReservationService]: cart is empty for cart_id {cart_id}. Skipping..")
            return

        inventory_values = await self._inventory_values(cart_items)

        stmt = (
            update(Inventory)
            .where(Inventory.product_id == inventory_values.c.product_id)
            .values(stock=Inventory.stock + inventory_values.c.qty)
            .returning(Inventory.product_id)
        )
        result_cursor = await self.session.scalars(stmt)
        result = result_cursor.all()

        logger.info(f"[InventoryReservationService]: releasing inventory result {result}")
        return result
