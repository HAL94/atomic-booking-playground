import asyncio
import logging
import random
import time
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import session_manager
from app.core.logging import configure_logging
from app.core.security.jwt import hash_password
from app.domain.auth import UserBase
from app.dto.bid import CreateAuctionBid
from app.models import AuctionWinner
from app.playground.reset_db import reset_db
from app.repositories.user_repository import UserRepository
from app.services.bid.service import BidService

configure_logging()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

AUCTION_ID = "6b91fa86-c200-4845-94f0-b221b2065e21"
BIDS_PER_USER = 100


class SharedPriceTracker:
    def __init__(self, start_price: float):
        self._price = start_price
        self._lock = asyncio.Lock()

    async def get_next_price(self) -> float:
        async with self._lock:
            # Guarantee every generated bid is higher than the last
            self._price = round(self._price + random.uniform(1.0, 2.5), 2)
            return self._price


def create_user(id_sequence: str, number_sequence: int):
    return UserBase(
        id=UUID("3cd57e13-93e1-4d54-ac68-a23a541b9" + id_sequence),
        full_name=f"Bidder {number_sequence}",
        email=f"bu{number_sequence}@example.com",
        hashed_password=hash_password("123456"),
    )


async def upsert_bidding_users(number_of_users: int = 10) -> list[UserBase]:
    async with session_manager.session() as session:
        user_repo = UserRepository(session)
        SUFFIX = 478
        payload = []
        for i in range(number_of_users):
            payload.append(create_user(str(SUFFIX), i + 1))
            SUFFIX += 1
        index_elements = ["id"]

        return await user_repo.upsert(payload, index_elements, commit=True)


async def fetch_current_highest_price() -> float:
    """Reads current price without holding locks (simulates UI fetch)."""
    async with session_manager.session() as session:
        query = (
            select(AuctionWinner)
            .where(AuctionWinner.auction_id == AUCTION_ID)
            .options(selectinload(AuctionWinner.winning_bid))
        )
        res = (await session.execute(query)).scalar_one_or_none()
        if res and res.winning_bid:
            return float(res.winning_bid.amount)
        return 10.0  # Base starting price


async def simulate_bids_for_user(user_id: str, price_tracker: SharedPriceTracker):
    """Simulates a user submitting a rapid sequence of incremental bids."""
    bids_successful = 0
    bids_rejected = 0

    for i in range(BIDS_PER_USER):
        # 1. Open a FRESH session per bid request (mimics individual HTTP requests)
        async with session_manager.session() as session:
            bid_service = BidService(session)
            try:
                # 2. Fetch current baseline (unlocked read)
                current_price = await price_tracker.get_next_price()

                # 3. Add increment + random jitter (e.g., +1.00 to +3.00)
                increment = round(random.uniform(1.0, 3.0), 2)
                target_amount = round(current_price + increment, 2)

                # 4. Attempt insertion via BidService (which executes FOR UPDATE)
                await bid_service.create_bid(
                    CreateAuctionBid(
                        bid_amount=int(target_amount),
                        user_id=user_id,
                        auction_id=AUCTION_ID,
                    )
                )
                bids_successful += 1

            except Exception as e:
                # Expected when another concurrent transaction locked & raised price first
                bids_rejected += 1
                logger.debug(f"Bid rejected for user {user_id}: {e}")

        # 5. Small jitter (1-5ms) to interleave requests across tasks
        await asyncio.sleep(random.uniform(0.001, 0.005))

    logger.info(
        f"[BidsSimulator]: User {user_id} finished -> Success: {bids_successful}, Rejected/Failed: {bids_rejected}"
    )



async def run_contention_test():
    await reset_db()
    bidders = await upsert_bidding_users()
    total_expected_bids = len(bidders) * BIDS_PER_USER

    # In run_contention_test:
    price_tracker = SharedPriceTracker(start_price=10.0)

    print(f"\n🚀 Injecting {total_expected_bids} bids across {len(bidders)} concurrent tasks...")
    start_time = time.perf_counter()

    # Run all bidder loops concurrently
    tasks = [simulate_bids_for_user(str(u.id), price_tracker) for u in bidders]
    await asyncio.gather(*tasks)

    elapsed = time.perf_counter() - start_time
    req_per_sec = total_expected_bids / elapsed if elapsed > 0 else 0

    print("\n================ BENCHMARK RESULTS ================")
    print(f"Total Bids Attempted: {total_expected_bids}")
    print(f"Elapsed Time:          {elapsed:.3f} seconds")
    print(f"Throughput:            {req_per_sec:.1f} req/sec")
    print("====================================================\n")


if __name__ == "__main__":
    asyncio.run(run_contention_test())
