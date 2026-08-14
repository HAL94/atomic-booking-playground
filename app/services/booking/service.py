import logging
from typing import Optional
from uuid import UUID

from app.domain.booking import BookingBase
from app.dto.booking import CreateReservation
from app.models import Booking
from app.repositories.booking_repository import BookingRepository
from app.services.base import BaseService
from app.services.booking.reservation import ReservationHoldout

logger = logging.getLogger("uvicorn")
logger.setLevel(logging.INFO)


class BookingService(BaseService):
    def __init__(self, session):
        super().__init__(session)
        self._booking_repo = BookingRepository(session)
        self._reservation = ReservationHoldout(session)

    async def get_booking(self, booking_id: UUID, user_id: UUID):
        """
        Retrieve a booking by id owned by a user
        """
        return await self._booking_repo.get_one([Booking.id == booking_id, Booking.user_id == user_id])

    async def create_reservation(self, payload: CreateReservation, user_id: UUID) -> Optional[BookingBase]:
        """
        Create a reservation (a temporary hold booking) for a given user
        """
        return await self._reservation.reserve_booking(payload, user_id)
