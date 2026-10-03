from typing import ClassVar

from sqlalchemy import insert, select

from app.core.exceptions import NotFoundException
from app.domain.cart import CartBase, CartItemBase
from app.domain.cart_status import CartStatus
from app.dto.cart import AddItemDto, UpdateItemOp
from app.models import Cart
from app.repositories.base_repository import BaseRepository
from app.repositories.cart_item_repository import CartItemRepository
from app.services.inventory_reservation import InventoryReservationService


class CartRepository(BaseRepository[CartBase, Cart]):
    __model__: ClassVar[Cart] = Cart

    def __init__(self, session):
        super().__init__(session)
        self._cart_item_repo = CartItemRepository(session)
        self._inv_repo = InventoryReservationService(session)

    def domain_model(self, data, as_domain=None):
        if as_domain:
            return as_domain.model_validate(data, from_attributes=True)
        return CartBase.model_validate(data, from_attributes=True)

    async def get_active_cart(self, user_id: str, raise_for_not_found: bool = True) -> Cart | None:
        stmt = select(Cart).where(Cart.customer_id == user_id, Cart.status == CartStatus.ACTIVE)
        cart = await self.session.scalar(stmt)
        if not cart and raise_for_not_found:
            raise NotFoundException(f"Cart for customer {user_id} does not exist")
        return cart

    async def create_cart(self, user_id: str) -> Cart:
        cart_base = CartBase(status=CartStatus.ACTIVE, customer_id=user_id)
        stmt = insert(Cart).values(**cart_base.model_dump(exclude_none=True)).returning(Cart)
        return await self.session.scalar(stmt)

    async def remove_item(self, cart_item_id: str, user_id: str) -> CartItemBase:
        cart = await self.get_active_cart(user_id)
        await self._inv_repo.release_inventory(cart.id, user_id, cart.cart_items)

        cart_item_removed = await self._cart_item_repo.remove_item(cart_item_id, user_id, cart.id)
        # await self.session.refresh(cart)
        cart.total = cart.cart_total

        await self.session.commit()

        return cart_item_removed

    async def update_item(self, cart_item_id: str, user_id: str, update_op: UpdateItemOp) -> CartItemBase:
        cart = await self.get_active_cart(user_id)
        await self._inv_repo.release_inventory(cart.id, user_id, cart.cart_items)
        cart_item_updated = await self._cart_item_repo.update_item(
            user_id=user_id, cart_item_id=cart_item_id, cart_id=cart.id, update_op=update_op
        )
        await self.session.refresh(cart)
        cart.total = cart.cart_items

        await self.session.commit()
        return cart_item_updated

    async def add_item(self, item: AddItemDto, user_id: str) -> CartItemBase:
        cart = await self.get_active_cart(user_id, raise_for_not_found=False)
        if not cart:
            cart = await self.create_cart(user_id)
        await self._inv_repo.release_inventory(cart.id, user_id, cart.cart_items)
        result = await self._cart_item_repo.add_item(item, user_id, cart.id)
        await self.session.refresh(cart)
        cart.total = cart.cart_total

        await self.session.commit()
        return result
