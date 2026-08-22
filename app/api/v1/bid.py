from uuid import UUID

from fastapi import APIRouter

from app.core.pagination import PaginatedResult
from app.core.schema import AppResponse
from app.dependencies.db_session import DbSession
from app.domain.bid import BidBase
from app.services.bid import BidService

bid_router = APIRouter(prefix="/bids", tags=["Bids"])


@bid_router.get("/{auction_id}")
async def get_bids(session: DbSession, auction_id: UUID) -> AppResponse[PaginatedResult[BidBase]]:
    """
    Retrieve a list of auctions owned by a user
    """
    service = BidService(session)
    result = await service.get_auction_bids(auction_id)
    return AppResponse(data=result)
