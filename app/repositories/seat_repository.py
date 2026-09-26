from typing import ClassVar

from app.domain.seat import SeatBase
from app.models import Seat
from app.repositories.base_repository import BaseRepository


class SeatRepository(BaseRepository[SeatBase, Seat]):
    __model__: ClassVar[Seat] = Seat

    def __init__(self, session):
        super().__init__(session)

    def domain_model(self, data, as_domain=None):
        if as_domain:
            return as_domain.model_validate(data, from_attributes=True)
        return SeatBase.model_validate(data, from_attributes=True)
