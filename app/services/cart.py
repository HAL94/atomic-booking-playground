import logging

from app.domain.cart import CartBase, CartItemBase
from app.dto.cart import AddItemDto, UpdateItemOp
from app.repositories.cart_repository import CartRepository
from app.services.base import BaseService

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class CartService(BaseService):
    def __init__(self, session):
        super().__init__(session)
        self._cart_repo = CartRepository(session)

    async def get_cart(self, user_id: str) -> CartBase:
        cart = await self._cart_repo.get_active_cart(user_id)
        logger.info(f"[CartService] cart total {cart.cart_total}")
        return CartBase.model_validate(cart, from_attributes=True)

    async def remove_item(self, cart_item_id: str, user_id: str) -> CartItemBase:
        item = await self._cart_repo.remove_item(cart_item_id=cart_item_id, user_id=user_id)
        return item

    async def update_item(self, cart_item_id: str, user_id: str, update_op: UpdateItemOp) -> CartItemBase:
        return await self._cart_repo.update_item(cart_item_id=cart_item_id, user_id=user_id, update_op=update_op)

    async def add_item(self, item: AddItemDto, user_id: str) -> CartItemBase:
        return await self._cart_repo.add_item(item=item, user_id=user_id)
