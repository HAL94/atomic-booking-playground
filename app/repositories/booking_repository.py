from typing import ClassVar

from app.domain.booking import BookingBase
from app.models import Booking
from app.repositories.base_repository import BaseRepository


class BookingRepository(BaseRepository[BookingBase, Booking]):
    __model__: ClassVar[Booking] = Booking

    def domain_model(self, data, as_domain=None):
        if as_domain:
            return as_domain.model_validate(data, from_attributes=True)
        return BookingBase.model_validate(data, from_attributes=True)
