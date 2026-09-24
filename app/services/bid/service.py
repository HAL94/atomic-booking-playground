from uuid import UUID

from app.core.pagination import PaginatedResult
from app.domain.bid import BidBase
from app.dto.bid import CreateAuctionBid
from app.models import Auction, Bid
from app.repositories.auction_repository import AuctionRepository
from app.repositories.bid_repository import BidRepository
from app.services.base import BaseService


class BidService(BaseService):
    def __init__(self, session):
        super().__init__(session)
        self._bid_repo = BidRepository(session)
        self._auction_repo = AuctionRepository(session)

    async def get_auction_bids(self, auction_id: UUID | str) -> PaginatedResult[BidBase]:
        return await self._bid_repo.get_many(where_clause=[Bid.auction_id == auction_id])

    async def create_bid(self, payload: CreateAuctionBid) -> BidBase:
        # check for existance, method throws NotFoundException
        await self._auction_repo.get_one([Auction.id == payload.auction_id])
        return await self._bid_repo.insert_bid_by_sql_check(payload)
