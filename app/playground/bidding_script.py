import asyncio
import logging
import random
from datetime import datetime, timezone

from sqlalchemy import delete, insert, select, text, update

from app.core.database import session_manager
from app.core.logging import configure_logging
from app.domain.bid_inbox import BidInboxBase
from app.domain.bid_status import BidStatus
from app.models import Auction, Bid, BidInbox, User

configure_logging()
logger = logging.getLogger(__name__)


class SharedPriceTracker:
    def __init__(self, start_price: float):
        self._price = start_price
        self._lock = asyncio.Lock()

    async def get_next_price(self) -> float:
        async with self._lock:
            self._price = round(self._price + random.uniform(1.0, 2.5), 2)
            return self._price

async def reset():
    async with session_manager.session() as session:
        await session.execute(text("TRUNCATE TABLE bids RESTART IDENTITY;"))
        await session.execute(delete(BidInbox))
        await session.execute(delete(Bid))
        await session.execute(update(Auction).values(highest_bid=None))
        await session.commit()
        logger.info("Reset DB done.")


async def insert_bids_for_all_auctions() -> int:
    async with session_manager.session() as session:
        auctions = (await session.scalars(select(Auction).order_by(Auction.id))).all()
        if not auctions:
            logger.info("No auctions found; no bids were added to the inbox.")
            return 0

        user_ids = (await session.scalars(select(User.id).order_by(User.id))).all()
        if not user_ids:
            raise RuntimeError("Cannot add bids to the inbox because the database has no users.")
        total = 0
        bets = random.randint(50, 200)
        total += bets * 3
        for _, auction in enumerate(auctions):
            # price_tracker = SharedPriceTracker(10)
            eligible_user_ids = [user_id for user_id in user_ids if user_id != auction.auction_owner_id]
            if not eligible_user_ids:
                raise RuntimeError(f"Cannot add a bid for auction {auction.id}: no non-owner users are available.")

            for _ in range(bets):
                bid_amount = random.randint(10, 1000)
                await session.execute(
                    insert(BidInbox).values(
                        BidInboxBase(
                            auction_id=auction.id,
                            user_id=random.choice(eligible_user_ids),
                            amount=round(bid_amount, 2),
                            status=BidStatus.PENDING,
                            created_at=datetime.now(tz=timezone.utc),
                        ).model_dump(exclude_none=True)
                    )
                )
                await asyncio.sleep(random.uniform(0.001, 0.025))

        await session.commit()

    logger.info("Added %d pending bids to the inbox for %d auctions.", total, len(auctions))


async def main():
    await reset()
    await insert_bids_for_all_auctions()


if __name__ == "__main__":
    asyncio.run(main())
