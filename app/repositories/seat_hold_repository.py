from typing import ClassVar

from app.domain.seat_hold import SeatHoldBase
from app.models import SeatHold
from app.repositories.base_repository import BaseRepository


class SeatHoldRepository(BaseRepository[SeatHoldBase, SeatHold]):
    __model__: ClassVar[SeatHold] = SeatHold

    def __init__(self, session):
        super().__init__(session)

    def domain_model(self, data, as_domain=None):
        if as_domain:
            return as_domain.model_validate(data, from_attributes=True)
        return SeatHoldBase.model_validate(data, from_attributes=True)
