from fastapi import APIRouter

from .auction import auction_router
from .auth import auth_router
from .bid import bid_router

v1_router = APIRouter(prefix="/v1")


@v1_router.get("/welcome")
def welcome():
    return {"Welcome": "to your seed project"}


v1_router.include_router(auction_router)
v1_router.include_router(bid_router)
v1_router.include_router(auth_router)
