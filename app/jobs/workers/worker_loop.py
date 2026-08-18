import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update

from app.core.database import session_manager
from app.domain.booking_status import BookingStatus
from app.models import Booking, Seat

logger = logging.getLogger(__name__)

async def run_worker_loop(worker_id: int):
    try:
        async with session_manager.session() as session:
            cutoff = datetime.now(tz=timezone.utc) - timedelta(seconds=60)
            stmt = (
                select(Booking, Seat)
                .join(Seat, Booking.seat_id == Seat.id)
                .where(Booking.status == BookingStatus.PENDING, Booking.reserved_at <= cutoff)
                .with_for_update(skip_locked=True, of=[Booking, Seat])
                .limit(100)
            )

            result_tuple = (await session.execute(stmt)).all()

            booking_ids = [b.id for b, _ in result_tuple]
            seat_ids = [s.id for _, s in result_tuple]

            stmt = (
                update(Booking)
                .values(canceled_at=datetime.now(timezone.utc), status=BookingStatus.CANCELED)
                .where(Booking.id.in_(booking_ids))
            )
            update_booking_result = await session.execute(stmt)
            logger.info(f"[BookingSweeper worker {worker_id}] canceled {update_booking_result.rowcount} booking(s)")

            stmt = (
                update(Seat).values(is_held=False).where(Seat.id.in_(seat_ids))  # noqa: E712
            )
            update_seat_result = await session.execute(stmt)
            logger.info(
                f"[BookingSweeper worker {worker_id}] reset {update_seat_result.rowcount} seat(s) back to unheld"
            )

            await session.commit()
    except Exception as e:
        logger.exception(f"[BookingSweeper worker {worker_id}] Error during DB sweep: {e}")
