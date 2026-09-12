import logging
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.database import session_manager
from app.models import Bid
from app.redis_client.client import RedisClient

logger = logging.getLogger(__name__)

STREAM_NAME = "bids:vinteage"
CONSUMER_GROUP = "vintage_db_sync"
CONSUMER_NAME = "worker_node_{worker_id}"
WOKRER_PREFIX = "BidSweeper worker {worker_id}"

WORKER_DRAINED_PEL: dict[str, bool] = dict()


async def init_consumer_group(redis: RedisClient):
    try:
        # Create group starting at beginning of stream ('0')
        await redis._client.xgroup_create(STREAM_NAME, CONSUMER_GROUP, id="0", mkstream=True)
    except Exception as e:
        if "BUSYGROUP" not in str(e):
            raise


async def process_batch(redis: RedisClient, entries: list):
    records = []
    stream_ids = []

    if len(entries) == 0:
        logger.info("[BidSweeper.__process_batch]: no records, return early..")

    for stream_id, payload in entries:
        s_id = stream_id.decode() if isinstance(stream_id, bytes) else stream_id
        bid_ts, bid_seq = s_id.split("-")
        records.append(
            {
                "bid_seq": int(bid_seq),
                "bid_ts": int(bid_ts),
                "amount": float(payload[b"current_highest"].decode()),
                "auction_id": UUID(payload[b"auction_id"].decode()),
                "user_id": UUID(payload[b"user_id"].decode()),
            }
        )

        stream_ids.append(s_id)

    if not records:
        return

    logger.info(f"[BidSweeper.__process_batch]: records {records}")
    # Ack messages in Redis AFTER successful DB commit
    async with session_manager.session() as session:
        stmt = pg_insert(Bid).values(records).on_conflict_do_nothing(index_elements=["bid_seq", "bid_ts"])
        await session.execute(stmt)
        await session.commit()

    await redis._client.xackdel(STREAM_NAME, CONSUMER_GROUP, *stream_ids)
    # await redis.xackdel(STREAM_NAME, CONSUMER_GROUP, stream_ids)
    return stream_ids


async def drain_own_pending_on_startup(redis: RedisClient, worker_id: str):
    """Fetch and process un-ACKed items assigned to THIS consumer from a past life."""
    if worker_id in WORKER_DRAINED_PEL:
        return
    try:
        logger.info(f"[{WOKRER_PREFIX.format(worker_id=worker_id)}]: started and is draining its own PEL pool...")
        """
            Messages in the group's Pending Entries List (PEL) that were already assigned to this consumer name,
            starting from the smallest pending ID (0-0).
        """
        while True:
            response = await redis._client.xreadgroup(
                groupname=CONSUMER_GROUP,
                consumername=CONSUMER_NAME.format(worker_id=worker_id),
                streams={STREAM_NAME: "0"},  # "0" reads this consumer's pending entries
                count=100,
            )
            if not response:
                break

            _, entries = response[0]

            if not entries:
                logger.info(f"[{WOKRER_PREFIX.format(worker_id=worker_id)}]: consumer has no pending entries...")
                break

            await process_batch(redis, entries)
    finally:
        WORKER_DRAINED_PEL[worker_id] = True


async def bid_processor_loop(worker_id: str, redis: RedisClient):
    await init_consumer_group(redis)
    try:
        logger.info(f"[{WOKRER_PREFIX.format(worker_id=worker_id)}] listening for entries...")
        await drain_own_pending_on_startup(redis, worker_id)
        """
          When a worker calls XREADGROUP ... STREAMS bids:vintage >,
          the > operator tells Redis: "Deliver entries that have never been delivered to any consumer in this group yet.
        """
        response = await redis._client.xreadgroup(
            groupname=CONSUMER_GROUP,
            consumername=CONSUMER_NAME.format(worker_id=worker_id),
            streams={STREAM_NAME: ">"},  # >: get entries not seen by any consumers thus far
            count=100,
            block=2000,
        )
        if response:
            _, entries = response[0]
            logger.info(f"[{WOKRER_PREFIX.format(worker_id=worker_id)}]: entries {entries}, underscore {_}")
            await process_batch(redis, entries)

        # Periodically claim abandoned messages from dead workers (> 60s idle)
        """
            XAUTOCLAIM scans a consumer group's Pending Entries List (PEL), finds entries that have been pending
            (un-ACKed) for longer than a specified time (min_idle_time), and transfers ownership of those entries
            to a new consumer in a single atomic operation.
        """
        autoclaim_cursor = "0-0"
        claimed = await redis._client.xautoclaim(
            name=STREAM_NAME,
            groupname=CONSUMER_GROUP,
            consumername=CONSUMER_NAME.format(worker_id=worker_id),
            min_idle_time=60000,
            start_id=autoclaim_cursor,
            count=50,
        )
        if claimed:
            autoclaim_cursor = claimed[0] or autoclaim_cursor
            entries = claimed[1]
            if entries:
                logger.info(f"[{WOKRER_PREFIX.format(worker_id=worker_id)}]: abandoned entries {entries}")
                await process_batch(redis, entries)
    except Exception as e:
        logger.exception(f"[{WOKRER_PREFIX.format(worker_id=worker_id)}] Error during DB sweep: {e}")
