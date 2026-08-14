from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from app.core.schema import AppResponse
from app.dependencies.auth import CurrentUser, get_current_active_user
from app.dependencies.booking import BookingIdempotency
from app.dependencies.db_session import DbSession
from app.domain.booking import BookingBase
from app.dto.booking import CreateReservation
from app.services.booking.service import BookingService

booking_router = APIRouter(prefix="/bookings", tags=["Booking"], dependencies=[Depends(get_current_active_user)])


@booking_router.get("/{booking_id}", response_model=AppResponse[BookingBase])
async def get_booking(booking_id: UUID, user: CurrentUser, session: DbSession) -> AppResponse[BookingBase]:
    """
    Retrieve a booking made by a user
    """
    service = BookingService(session)
    result = await service.get_booking(booking_id, user.id)
    return AppResponse(data=result)


@booking_router.post("/reserve", response_model=AppResponse[BookingBase])
async def create_reservation(
    payload: CreateReservation,
    user: CurrentUser,
    session: DbSession,
    request: Request,
    cached_response: Optional[BookingBase] = Depends(BookingIdempotency()),
) -> AppResponse[BookingBase]:
    """
    Create temporary booking for a given user
    """
    if cached_response:
        return AppResponse(data=cached_response)

    try:
        service = BookingService(session)
        result = await service.create_reservation(payload, user.id)
        cache_key = getattr(request.state, "redis_cache_key", None)
        if cache_key:
            await BookingIdempotency.cache_booking_response(cache_key, result, status_code=201)
        return AppResponse(data=result)
    finally:
        lock_token = getattr(request.state, "lock_token", None)
        redis_lock_key = getattr(request.state, "redis_lock_key", None)
        await BookingIdempotency.clear_booking_cache_lock(redis_lock_key, lock_token)
