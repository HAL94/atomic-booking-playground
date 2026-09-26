from uuid import UUID

from fastapi import APIRouter

from app.core.schema import AppResponse
from app.dependencies.auth import CurrentUser
from app.dependencies.db_session import DbSession
from app.domain.seat_hold import SeatHoldBase
from app.services.booking import BookingService

booking_router = APIRouter(prefix="/bookings", tags=["Booking"])


@booking_router.get("/{hold_id}")
async def get_seat_hold(hold_id: UUID, user: CurrentUser, session: DbSession) -> AppResponse[SeatHoldBase]:
    try:
        service = BookingService(session=session)
        result = await service.get_seat_hold(str(hold_id), str(user.id))
        return AppResponse(data=result)
    except Exception as e:
        raise e

@booking_router.post("/hold/{seat_id}")
async def hold_seat(seat_id: UUID, user: CurrentUser, session: DbSession) -> AppResponse[SeatHoldBase]:
    try:
        service = BookingService(session=session)
        result = await service.try_hold_seat(str(seat_id), str(user.id))
        return AppResponse(data=result)
    except Exception as e:
        raise e
