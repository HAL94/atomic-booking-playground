from uuid import UUID

from fastapi import APIRouter

from app.core.pagination import PaginatedResult
from app.core.schema import AppResponse
from app.dependencies.auth import CurrentUser
from app.dependencies.db_session import DbSession
from app.domain.bid import BidBase
from app.dto.bid import CreateAuctionBid, CreateBidAmount, CreateBidResponse
from app.services.bid.service import BidService

bid_router = APIRouter(prefix="/bids", tags=["Bids"])


@bid_router.get("/{auction_id}")
async def get_bids(session: DbSession, auction_id: UUID) -> AppResponse[PaginatedResult[BidBase]]:
    """
    Retrieve a list of auctions owned by a user
    """
    service = BidService(session)
    result = await service.get_auction_bids(auction_id)
    return AppResponse(data=result)


@bid_router.post("/{auction_id}")
async def create_bid(
    session: DbSession, user: CurrentUser, auction_id: UUID, bid_payload: CreateBidAmount
) -> AppResponse[CreateBidResponse]:
    """
    Create a bid
    """
    service = BidService(session)
    payload = CreateAuctionBid(bid_amount=bid_payload.bid_amount, user_id=str(user.id), auction_id=str(auction_id))
    result = await service.create_bid(payload)
    return AppResponse(data=result)
