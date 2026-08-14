from fastapi import APIRouter

from .auth import auth_router
from .booking import booking_router

v1_router = APIRouter(prefix="/v1")


@v1_router.get("/welcome")
def welcome():
    return {"Welcome": "to your seed project"}


v1_router.include_router(booking_router)
v1_router.include_router(auth_router)
