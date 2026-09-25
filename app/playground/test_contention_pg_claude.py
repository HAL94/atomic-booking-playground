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

from sqlalchemy import func, select

from app.core.database import session_manager
from app.core.logging import configure_logging
from app.core.security.jwt import hash_password
from app.domain.auth import UserBase
from app.dto.bid import CreateAuctionBid
from app.models import Auction, Bid
from app.playground.reset_db import reset_db
from app.repositories.user_repository import UserRepository
from app.services.bid.service import BidService

configure_logging()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

AUCTION_ID = "6b91fa86-c200-4845-94f0-b221b2065e21"
MIN_BID_ATTEMPT = 2
MAX_BID_ATTEMPT = 5


@dataclass
class RunResult:
    num_bidders: int
    attempted: int = 0
    successful: int = 0
    rejected: int = 0
    elapsed: float = 0.0
    invariant_violations: int = 0

    @property
    def throughput(self) -> float:
        return self.attempted / self.elapsed if self.elapsed > 0 else 0.0


class SharedPriceTracker:
    """Mimics clients bidding off a slightly stale view of the current price.
    Deliberately not synchronized with the server's true state - that's what
    makes this a genuine contention test rather than a sequence of bids that
    are always trivially valid."""

    def __init__(self, start_price: float):
        self._price = start_price
        self._lock = asyncio.Lock()

    async def get_next_price(self) -> float:
        async with self._lock:
            self._price = round(self._price + random.uniform(1.0, 2.5), 2)
            return self._price


def create_user(id_sequence: str, number_sequence: int) -> UserBase:
    return UserBase(
        id=UUID("3cd57e13-93e1-4d54-ac68-a23a541b9" + id_sequence),
        full_name=f"Bidder {number_sequence}",
        email=f"bu{number_sequence}@example.com",
        hashed_password=hash_password("123456"),
    )


async def upsert_bidding_users(number_of_users: int) -> List[UserBase]:
    async with session_manager.session() as session:
        user_repo = UserRepository(session)
        suffix = 478
        payload = []
        for i in range(number_of_users):
            payload.append(create_user(str(suffix), i + 1))
            suffix += 1
        return await user_repo.upsert(payload, ["id"], commit=True)


async def simulate_bids_for_user(user_id: str, price_tracker: SharedPriceTracker, result: RunResult) -> None:
    bids_successful = 0
    bids_rejected = 0
    num_bids_to_make = random.randint(MIN_BID_ATTEMPT, MAX_BID_ATTEMPT)

    for _ in range(num_bids_to_make):
        # Fresh session per bid, mimicking individual HTTP requests
        async with session_manager.session() as session:
            bid_service = BidService(session)
            try:
                current_price = await price_tracker.get_next_price()
                increment = round(random.uniform(1.0, 3.0), 2)
                target_amount = int(round(current_price + increment))

                bid_created = await bid_service.create_bid(
                    CreateAuctionBid(
                        bid_amount=target_amount,
                        user_id=user_id,
                        auction_id=AUCTION_ID,
                    )
                )
                if not bid_created:
                    bids_rejected += 1
                else:
                    bids_successful += 1
            except Exception as e:
                # Expected: another concurrent bid locked & raised the price
                # first, or the lock wait itself failed/timed out.
                bids_rejected += 1
                logger.debug(f"Bid rejected for user {user_id}: {e}")

        await asyncio.sleep(random.uniform(0.05, 0.25))

    logger.info(
        f"[BidsSimulator]: User {user_id} finished -> Success: {bids_successful}, Rejected/Failed: {bids_rejected}"
    )
    result.attempted += num_bids_to_make
    result.successful += bids_successful
    result.rejected += bids_rejected


async def verify_bid_ordering_invariant(auction_id: str) -> int:
    """Every persisted bid must be strictly higher than the one before it,
    by construction of the `amount >= max + 1` guard in
    insert_bid_by_sql_check. A violation proves the guard evaluated against
    a stale MAX(Bid.amount) read - i.e. the snapshot/EvalPlanQual race,
    not a logic error in the SQL itself."""
    async with session_manager.session() as session:
        rows = (
            await session.execute(
                select(Bid.amount, Bid.created_at).where(Bid.auction_id == auction_id).order_by(Bid.created_at)
            )
        ).all()

    violations = 0
    prev_amount = None
    for amount, created_at in rows:
        if prev_amount is not None and amount <= prev_amount:
            violations += 1
            logger.warning(
                f"[Invariant violation] bid amount {amount} at {created_at} "
                f"did not exceed previous amount {prev_amount}"
            )
        prev_amount = amount

    return violations


async def verify_auction_highest_bid_consistency(auction_id: str) -> bool:
    """Auction.highest_bid is denormalized off the Bid table. Confirms it
    hasn't drifted from the true MAX(Bid.amount) - would catch any code
    path that writes a Bid without going through insert_bid_by_sql_check's
    matching Auction update, or any bug in that update itself."""
    async with session_manager.session() as session:
        auction_highest = (
            await session.execute(select(Auction.highest_bid).where(Auction.id == auction_id))
        ).scalar_one_or_none()
        true_max = (
            await session.execute(select(func.max(Bid.amount)).where(Bid.auction_id == auction_id))
        ).scalar_one_or_none()

    consistent = auction_highest == true_max
    if not consistent:
        logger.warning(
            f"[Consistency violation] Auction.highest_bid={auction_highest} but true MAX(Bid.amount)={true_max}"
        )
    return consistent


async def test_first_bid_lower_bound_bug() -> bool:
    """Regression check for the `highest_bid IS NULL` branch: as written,
    a NULL highest_bid short-circuits the amount comparison entirely, so
    the very first bid on a fresh auction is accepted regardless of its
    value - including zero or negative amounts. Returns True if the bug
    is present (i.e. the lowball bid was wrongly accepted)."""
    await reset_db()
    users = await upsert_bidding_users(1)
    user = users[0]

    accepted = False
    async with session_manager.session() as session:
        bid_service = BidService(session)
        try:
            is_inserted = await bid_service.create_bid(
                CreateAuctionBid(bid_amount=-50, user_id=str(user.id), auction_id=AUCTION_ID)
            )
            accepted = is_inserted is not None
        except Exception as e:
            logger.info(f"First bid of -50 correctly rejected: {e}")

    if accepted:
        logger.warning(
            "[Bug reproduced] A first bid of -50 was accepted because "
            "highest_bid IS NULL bypasses the amount check entirely."
        )
    else:
        logger.info("[OK] First-bid lower bound is enforced.")

    return accepted


async def run_contention_test(num_bidders: int) -> RunResult:
    await reset_db()
    bidders = await upsert_bidding_users(num_bidders)
    result = RunResult(num_bidders=num_bidders)
    price_tracker = SharedPriceTracker(start_price=10.0)

    print(
        f"\nInjecting bids across {len(bidders)} concurrent bidders ({MIN_BID_ATTEMPT}-{MAX_BID_ATTEMPT} bids each)..."
    )
    start_time = time.perf_counter()

    tasks = [simulate_bids_for_user(str(u.id), price_tracker, result) for u in bidders]
    await asyncio.gather(*tasks)

    result.elapsed = time.perf_counter() - start_time
    result.invariant_violations = await verify_bid_ordering_invariant(AUCTION_ID)
    consistent = await verify_auction_highest_bid_consistency(AUCTION_ID)

    print("\n================ BENCHMARK RESULTS ================")
    print(f"Bidders:               {result.num_bidders}")
    print(f"Total Bids Attempted:  {result.attempted}")
    print(f"Successful Bids:       {result.successful}")
    print(f"Rejected Bids:         {result.rejected}")
    print(f"Elapsed Time:          {result.elapsed:.3f} seconds")
    print(f"Throughput:            {result.throughput:.1f} req/sec")
    print(f"Invariant Violations:  {result.invariant_violations}")
    print(f"Auction/Bid Consistent:{'  ' if consistent else '  NO - '}{consistent}")
    print("====================================================\n")

    return result


async def find_degradation_point(bidder_levels: List[int]) -> None:
    """Sweeps concurrency levels to find where throughput plateaus or drops,
    and where lock-wait / connection-pool pressure starts producing
    invariant violations or outright errors rather than clean rejections."""
    results: List[RunResult] = []
    for n in bidder_levels:
        results.append(await run_contention_test(n))

    print("\n=============== DEGRADATION SUMMARY ===============")
    print(
        f"{'Bidders':>8} {'Attempted':>10} {'Success':>8} {'Rejected':>9} "
        f"{'Elapsed(s)':>11} {'Req/sec':>9} {'Violations':>11}"
    )
    for r in results:
        print(
            f"{r.num_bidders:>8} {r.attempted:>10} {r.successful:>8} "
            f"{r.rejected:>9} {r.elapsed:>11.3f} {r.throughput:>9.1f} "
            f"{r.invariant_violations:>11}"
        )
    print("====================================================\n")


async def main() -> None:
    bug_present = await test_first_bid_lower_bound_bug()
    print(f"\nFirst-bid lower-bound bug present: {bug_present}\n")

    # Single run:
    # await run_contention_test(num_bidders=10)

    # Sweep to find where throughput plateaus / degrades. Watch the
    # connection pool size in your engine config vs the bidder counts here -
    # that's the number most likely to explain any cliff you see.
    await find_degradation_point([5, 10, 25, 50, 100, 500])


if __name__ == "__main__":
    asyncio.run(main())
