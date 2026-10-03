import logging
from typing import ClassVar

from fastapi import HTTPException
from sqlalchemy import UUID, cast, delete, exists, insert, literal, not_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import InstrumentedAttribute

from app.core.exceptions import NotFoundException
from app.domain.cart import CartItemBase
from app.dto.cart import AddItemDto, UpdateItemOp
from app.models import CartItem, Product
from app.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class CartItemRepository(BaseRepository[CartItemBase, CartItem]):
    __model__: ClassVar[CartItem] = CartItem

    def __init__(self, session):
        super().__init__(session)

    def domain_model(self, data, as_domain=None):
        if as_domain:
            return as_domain.model_validate(data, from_attributes=True)
        return CartItemBase.model_validate(data, from_attributes=True)

    def _cart_where(self, cart_item_id: str, user_id: str, cart_id: str) -> list[InstrumentedAttribute]:
        return [CartItem.id == cart_item_id, CartItem.customer_id == user_id, CartItem.cart_id == cart_id]

    async def remove_item(self, cart_item_id: str, user_id: str, cart_id: str) -> CartItemBase:
        where_clause = self._cart_where(cart_item_id, user_id, cart_id)
        await self.get_one(where_clause)

        delete_cart_item_stmt = delete(CartItem).where(*where_clause).returning(CartItem)

        item_removed = await self.session.scalar(delete_cart_item_stmt)
        if not item_removed:
            raise HTTPException(status_code=404, detail="Could not remove such item")

        return self.domain_model(item_removed)

    async def update_item(self, cart_item_id: str, user_id: str, cart_id: str, update_op: UpdateItemOp) -> CartItemBase:
        where_clause = self._cart_where(cart_item_id, user_id, cart_id)
        stmt = select(CartItem).where(*where_clause)
        item = await self.session.scalar(stmt)
        if not item:
            raise NotFoundException()

        if update_op == UpdateItemOp.INC:
            item.quantity += 1
        elif update_op == UpdateItemOp.DEC:
            item.quantity -= 1

        if item.quantity > 10:
            raise HTTPException(status_code=409, detail="Item reached maximum allowed quantity to be added")
        if item.quantity <= 0:
            raise HTTPException(status_code=409, detail="Cannot decrement to 0 or less, please call delete API")

        return self.domain_model(item)

    async def add_item(self, item: AddItemDto, user_id: str, cart_id: str) -> CartItemBase:
        product = await self.session.get(Product, item.product_id)
        if not product:
            raise NotFoundException(f"Product id {item.product_id} not found")

        cart_item_base = CartItemBase(
            cart_id=cart_id,
            customer_id=user_id,
            quantity=1,
            product_id=product.id,
            unit_price_cents=product.price_cents,
        )
        insert_stmt = pg_insert(CartItem).values(**cart_item_base.model_dump(exclude_none=True)).returning(CartItem)
        insert_stmt = insert_stmt.on_conflict_do_nothing(index_elements=["cart_id", "product_id"])

        result = await self.session.scalar(insert_stmt)

        if not result:
            raise HTTPException(status_code=409, detail="Product already exists, please call update API")

        return self.domain_model(result)
