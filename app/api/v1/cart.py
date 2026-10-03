from uuid import UUID

from fastapi import APIRouter

from app.core.schema import AppResponse
from app.dependencies.auth import CurrentUser
from app.dependencies.db_session import DbSession
from app.domain.cart import CartBase, CartItemBase
from app.dto.cart import AddItemDto, CartItemUpdateDto
from app.services.cart import CartService

cart_router = APIRouter(prefix="/cart", tags=["Cart"])


@cart_router.post("/items")
async def add_item(item: AddItemDto, user: CurrentUser, session: DbSession) -> AppResponse[CartItemBase]:
    try:
        service = CartService(session)
        result = await service.add_item(item, str(user.id))
        return AppResponse(data=result)
    except Exception as e:
        raise e

@cart_router.get("/")
async def get_cart(user: CurrentUser, session: DbSession) -> AppResponse[CartBase]:
    try:
        service = CartService(session)
        result = await service.get_cart(str(user.id))
        return AppResponse(data=result)
    except Exception as e:
        raise e

@cart_router.patch("/items/{cart_item_id}")
async def update_item(
    cart_item_id: UUID, item_update: CartItemUpdateDto, user: CurrentUser, session: DbSession
) -> AppResponse[CartItemBase]:
    try:
        service = CartService(session)
        result = await service.update_item(str(cart_item_id), str(user.id), item_update.update_op)
        return AppResponse(data=result)
    except Exception as e:
        raise e

@cart_router.delete("/items/{cart_item_id}")
async def removed_item(
    cart_item_id: UUID, user: CurrentUser, session: DbSession
) -> AppResponse[CartItemBase]:
    try:
        service = CartService(session)
        result = await service.remove_item(str(cart_item_id), str(user.id))
        return AppResponse(data=result)
    except Exception as e:
        raise e

