import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update

from app.domain.booking_status import BookingStatus
from app.jobs.broker import broker
from app.jobs.deps import TdbSession
from app.models import Booking, Seat

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@broker.task(schedule=[{"interval": 10}])
async def booking_sweeper(session: TdbSession):
    logger.info("Let's execute this every 10s")
    cutoff = datetime.now(tz=timezone.utc) - timedelta(seconds=60)
    try:
        stmt = (
            select(Booking, Seat)
            .join(Seat, Booking.seat_id == Seat.id)
            .where(
                Booking.status == BookingStatus.PENDING,
                Booking.reserved_at <= cutoff,
            )
            .with_for_update(skip_locked=True, of=[Booking, Seat])
            .limit(100)
        )
        # Step 1: get a batch of bookings that lock-free (100 limit for a batch)
        booking_result_seq = (await session.execute(stmt)).all()

        if len(booking_result_seq) <= 0:
            logger.info("[booking_sweeper]: no bookings to sweep, returning..")
            return

        # Step 1-a: extract seat_ids
        seat_ids = [seat.id for _, seat in booking_result_seq]
        # Step 1-b: extract booking ids
        booking_ids = [booking.id for booking, _ in booking_result_seq]

        # Step 2: delete (softly) bookings
        stmt = (
            update(Booking)
            .where(Booking.id.in_(booking_ids))
            .values(canceled_at=datetime.now(), status=BookingStatus.CANCELED)
        )
        booking_cursor_result = await session.execute(stmt)
        logger.info(
            f"[booking_sweeper]: soft delete (status = Canceled) for {booking_cursor_result.rowcount} bookings.."
        )

        # Step 3: Reset status of resource (Seat)
        stmt = (
            update(Seat)
            .where(Seat.id.in_(seat_ids), Seat.is_held == True, Seat.is_booked == False)  # noqa: E712
            .values(is_held=False)
        )
        seat_cursor_result = await session.execute(stmt)
        logger.info(f"[booking_sweeper]: Reset {seat_cursor_result.rowcount} seats")

        await session.commit()

    except Exception as e:
        raise e
