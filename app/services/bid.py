from app.core.pagination import PaginatedResult
from app.domain.bid import BidBase
from app.models import Bid
from app.repositories.bid_repository import BidRepository
from app.services.base import BaseService


class BidService(BaseService):
    def __init__(self, session):
        super().__init__(session)
        self._bid_repo = BidRepository(session)

    async def get_auction_bids(self, auction_id: str) -> PaginatedResult[BidBase]:
        return await self._bid_repo.get_many(where_clause=[Bid.auction_id == auction_id])
