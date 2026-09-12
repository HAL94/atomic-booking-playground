from uuid import UUID

from app.core.pagination import PaginatedResult
from app.domain.bid import BidBase
from app.dto.bid import CreateAuctionBid, CreateBidResponse
from app.models import Bid
from app.repositories.bid_repository import BidRepository
from app.services.base import BaseService
from app.services.bid.enqueue_bid import BidEnqueue


class BidService(BaseService):
    def __init__(self, session):
        super().__init__(session)
        self._bid_repo = BidRepository(session)
        self._bid_queue = BidEnqueue()

    async def get_auction_bids(self, auction_id: UUID | str) -> PaginatedResult[BidBase]:
        return await self._bid_repo.get_many(where_clause=[Bid.auction_id == auction_id])

    async def create_bid(self, payload: CreateAuctionBid) -> CreateBidResponse:
        return await self._bid_queue.publish_bid(payload)
