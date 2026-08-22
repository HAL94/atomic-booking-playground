from fastapi import APIRouter

from app.core.pagination import PaginatedResult
from app.core.schema import AppResponse
from app.dependencies.auth import CurrentUser
from app.dependencies.db_session import DbSession
from app.domain.auction import AuctionBase
from app.services.auction import AuctionService

auction_router = APIRouter(prefix="/auctions", tags=["Auctions"])


@auction_router.get("/")
async def get_auctions(
    user: CurrentUser,
    session: DbSession,
) -> AppResponse[PaginatedResult[AuctionBase]]:
    """
    Retrieve a list of auctions owned by a user
    """
    service = AuctionService(session)
    result = await service.get_auctions_by_owner(user.id)
    return AppResponse(data=result)
