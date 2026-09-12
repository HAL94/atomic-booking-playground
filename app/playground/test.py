import asyncio
import logging
import random
import time
from uuid import UUID

from sqlalchemy import delete

from app.core.config import settings
from app.core.database import session_manager
from app.core.logging import configure_logging
from app.core.security.jwt import hash_password
from app.domain.auth import UserBase
from app.models import Bid
from app.playground.bidding_script import CreateAuctionBid, TestingBidEnqueue
from app.redis_client.client import RedisClient, RedisClientConfig
from app.repositories.user_repository import UserRepository

configure_logging()
logger = logging.getLogger(__name__)

REDIS_URL = "redis://redis:6379/0"
STREAM_NAME = "bids:vinteage"
AUCTION_ID = "6b91fa86-c200-4845-94f0-b221b2065e21"
AUCTION_KEY = f"bids:{AUCTION_ID}"

# Simulation configuration
TOTAL_BIDDERS = 2  # Concurrent simulated users
BIDS_PER_USER = 10  # Bids each user sends



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


async def simulate_bids_for_user(user_id: str, redis: RedisClient, bid_enqueue: TestingBidEnqueue):
    """Simulates a user submitting a rapid sequence of incremental bids."""
    bids_made = 0
    base_price = float((await redis._client.hget(AUCTION_KEY, "current_highest")) or 10.0)
    for i in range(BIDS_PER_USER):
        try:
            # Generate incrementing bid amounts
            # base_price = 10.0
            jitter = random.uniform(0.01, 0.25)
            amount = round(base_price + (i * 0.5) + jitter, 2)

            # Push directly to Stream (mimicking your FastAPI endpoint behavior)
            # await redis.xadd(STREAM_NAME, fields={"current_bid": amount})
            await bid_enqueue.publish_bid(
                CreateAuctionBid(bid_amount=int(amount), user_id=user_id, auction_id=AUCTION_ID)
            )

            # Small random jitter (0-5ms) to simulate network spread
            await asyncio.sleep(random.uniform(0.001, 0.005))
            bids_made += 1
        except Exception as e:
            logger.exception(f"[BidsSimulator]: failed to bid user_id: {user_id}, error: {str(e)}")
            continue

    logger.info(f"[BidsSimulator]: user {user_id} made {bids_made} bids")


async def reset_db_and_redis(redis: RedisClient):
    """
    Remove bid records and reset redis
    """
    try:
        async with session_manager.session() as session:
            await session.execute(delete(Bid))
            await session.commit()

        # await redis._client.hset(AUCTION_KEY, "current_highest", "0")
        await redis._client.delete(AUCTION_KEY)
        logger.info("[BidsSimulation]: successfully reset bids")

    except Exception as e:
        logger.exception(f"[BidsSimulation]: failed to reset bids and redis {str(e)}")
        raise e


async def run_contention_test():
    redis_config = RedisClientConfig(host=settings.REDIS_SERVER)
    redis = RedisClient(redis_config)
    await redis.connect()
    await reset_db_and_redis(redis)
    bidders = await upsert_bidding_users()

    logger.info(f"[BidsSimulator]: redis instantiated {redis}")

    bid_enqueue = TestingBidEnqueue(redis)

    TOTAL_EXPECTED_BIDS = len(bidders) * BIDS_PER_USER
    print(f"🚀 Injecting {TOTAL_EXPECTED_BIDS} bids across {len(bidders)} concurrent clients...")
    start_time = time.perf_counter()

    # Launch all user tasks concurrently
    tasks = [simulate_bids_for_user(str(u.id), redis, bid_enqueue) for u in bidders]
    await asyncio.gather(*tasks)

    elapsed = time.perf_counter() - start_time
    print(
        f"✅ Finished enqueueing {TOTAL_EXPECTED_BIDS} bids in {elapsed:.2f}s ({TOTAL_EXPECTED_BIDS / elapsed:.0f} \
            req/sec)."
    )
    await redis.disconnect()


if __name__ == "__main__":
    asyncio.run(run_contention_test())
