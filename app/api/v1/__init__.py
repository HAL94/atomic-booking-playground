from fastapi import APIRouter

from .auth import auth_router
from .checkout import checkout_router
from .cart import cart_router

v1_router = APIRouter(prefix="/v1")


@v1_router.get("/welcome")
def welcome():
    return {"Welcome": "to your seed project"}

v1_router.include_router(checkout_router)
v1_router.include_router(auth_router)
v1_router.include_router(cart_router)
