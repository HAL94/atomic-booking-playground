from uuid import UUID

from app.core.pagination import PaginatedResult
from app.domain.auction import AuctionBase
from app.models import Auction
from app.repositories.auction_repository import AuctionRepository
from app.services.base import BaseService


class AuctionService(BaseService):
    def __init__(self, session):
        super().__init__(session)
        self._auction_repo = AuctionRepository(session)

    async def get_auctions_by_owner(self, auction_owner_id: UUID) -> PaginatedResult[AuctionBase]:
        """
        Retrieve a list of auctions
        """
        return await self._auction_repo.get_many(where_clause=[Auction.auction_owner_id == auction_owner_id])
