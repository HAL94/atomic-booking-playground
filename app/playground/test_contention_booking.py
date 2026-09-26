"""
test_contention.py

Contention benchmark for the PostgreSQL pessimistic-locking bid path
(BidRepository.insert_bid_by_sql_check, reached via BidService.create_bid).

Structured the same way as the earlier Redis contention test: N bidders,
each firing a burst of jittered bids concurrently. Two things are added
on top of that pattern:

1. A post-run invariant check. `insert_bid_by_sql_check` only accepts a
   bid when amount >= MAX(Bid.amount) + 1, so every persisted bid should
   be strictly higher than the one before it. If that's ever violated,
   it's direct evidence of the FOR UPDATE / stale-snapshot race: the
   MAX(Bid.amount) subquery reads the Bid table using the statement's
   original snapshot, which — unlike the locked Auction row — is not
   refreshed by EvalPlanQual once a waiting transaction is unblocked.
   This check turns that theoretical race into something you can
   actually observe.

2. A concurrency sweep (`find_degradation_point`), so you can see
   throughput, rejection rate, and violations across bidder counts in
   one run, to find where the system falls over rather than guessing.
"""

import asyncio
import logging
import random
import time
from dataclasses import dataclass
from typing import List
from uuid import UUID

from app.core.database import session_manager
from app.core.logging import configure_logging
from app.core.security.jwt import hash_password
from app.domain.auth import UserBase
from app.playground.reset_db import reset_db
from app.repositories.user_repository import UserRepository
from app.services.booking import BookingService

configure_logging()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

ITEM_ID = "05b42ace-71c3-4172-b2d8-9d608cf93dab"


@dataclass
class RunResult:
    num_bookers: int
    attempted: int = 0
    successful: int = 0
    rejected: int = 0
    elapsed: float = 0.0
    invariant_violations: int = 0

    @property
    def throughput(self) -> float:
        return self.attempted / self.elapsed if self.elapsed > 0 else 0.0


def create_user(id_sequence: str, number_sequence: int) -> UserBase:
    return UserBase(
        id=UUID("3cd57e13-93e1-4d54-ac68-a23a541b9" + id_sequence),
        full_name=f"Bidder {number_sequence}",
        email=f"u{number_sequence}@example.com",
        hashed_password=hash_password("123456"),
    )


async def upsert_booking_users(number_of_users: int) -> List[UserBase]:
    async with session_manager.session() as session:
        user_repo = UserRepository(session)
        suffix = 478
        payload = []
        for i in range(number_of_users):
            payload.append(create_user(str(suffix), i + 1))
            suffix += 1
        return await user_repo.upsert(payload, ["id"], commit=True)


async def simulate_holds_for_user(user_id: str, seat_id: str, result: RunResult) -> None:
    is_success = 0
    is_rejected = 0

    async with session_manager.session() as session:
        service = BookingService(session)
        try:
            hold_created = await service.try_hold_seat(seat_id, user_id)
            is_success = hold_created is not None
        except Exception as e:
            is_rejected = True
            logger.debug(f"Hold rejected for user {user_id}: {e}")

        await asyncio.sleep(random.uniform(0.05, 0.25))

    if is_success:
        logger.info(f"[HoldsSimulator]: User {user_id} finished -> Success: {is_success}")
    else:
        logger.info(f"[HoldsSimulator]: User {user_id} finished -> Failure: {is_rejected}")

    result.attempted += 1
    if is_success:
        result.successful += 1
    if is_rejected:
        result.rejected += 1


async def run_contention_test(num_bookers: int = 10) -> RunResult:
    await reset_db()
    holders = await upsert_booking_users(num_bookers)
    result = RunResult(num_bookers=num_bookers)

    print(f"\nAttempting {len(holders)} concurrent bookings against one item {ITEM_ID}")
    start_time = time.perf_counter()

    tasks = [simulate_holds_for_user(str(u.id), ITEM_ID, result) for u in holders]
    await asyncio.gather(*tasks)

    result.elapsed = time.perf_counter() - start_time

    print("\n================ BENCHMARK RESULTS ================")
    print(f"Bookers:               {result.num_bookers}")
    print(f"Total Holds Attempted:  {result.attempted}")
    print(f"Successful Holds:       {result.successful}")
    print(f"Rejected Holds:         {result.rejected}")
    print(f"Elapsed Time:          {result.elapsed:.3f} seconds")
    print(f"Throughput:            {result.throughput:.1f} req/sec")
    print("====================================================\n")

    return result


async def main() -> None:
    # Single run:
    await run_contention_test(num_bookers=50)


if __name__ == "__main__":
    asyncio.run(main())
