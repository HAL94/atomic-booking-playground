from fastapi import APIRouter

from app.dependencies.auth import CurrentUser
from app.dependencies.db_session import DbSession
from app.services.checkout import CheckoutService

checkout_router = APIRouter(prefix="/checkout")


@checkout_router.post("/")
async def attempt_checkout(user: CurrentUser, session: DbSession):
    try:
        service = CheckoutService(session)
        await service.create_cart_reservation(str(user.id))
    except Exception as e:
        raise e
