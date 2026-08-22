from typing import ClassVar

from app.domain.auction import AuctionBase
from app.models import Auction
from app.repositories.base_repository import BaseRepository


class AuctionRepository(BaseRepository[AuctionBase, Auction]):
    __model__: ClassVar[Auction] = Auction

    def domain_model(self, data, as_domain=None):
        if as_domain:
            return as_domain.model_validate(data, from_attributes=True)
        return AuctionBase.model_validate(data, from_attributes=True)
