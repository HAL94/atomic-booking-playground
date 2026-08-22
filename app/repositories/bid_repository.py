from typing import ClassVar

from app.domain.bid import BidBase
from app.models import Bid
from app.repositories.base_repository import BaseRepository


class BidRepository(BaseRepository[BidBase, Bid]):
    __model__: ClassVar[Bid] = Bid

    def domain_model(self, data, as_domain=None):
        if as_domain:
            return as_domain.model_validate(data, from_attributes=True)
        return BidBase.model_validate(data, from_attributes=True)
