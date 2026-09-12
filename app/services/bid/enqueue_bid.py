import logging

from app.dependencies.redis import get_redis_client
from app.dto.bid import CreateAuctionBid, CreateBidResponse
from app.redis_client.client import RedisClient

logger = logging.getLogger(__name__)

AUCTION_KEY = "auctions:{auction_id}"
BID_KEY = "bids:{auction_id}"
STREAM_NAME = "bids:vinteage"

ADD_BID_SCRIPT = """
    -- HSET key
    local bid_key = KEYS[1]
    -- Fields
    local bid_field = KEYS[2]
    local auction_id_field = KEYS[3]
    local user_id_field = KEYS[4]
    -- Values
    local bid_value = tonumber(ARGV[1])
    local auction_id_value = ARGV[2]
    local user_id_value = ARGV[3]

    if not bid_value then
        return redis.error_reply("ERR: bid_value must be a valid number")
    end

    local current_high = redis.call("HGET", bid_key, bid_field)
    if not current_high then
        redis.call("HSET", bid_key, bid_field, bid_value, auction_id_field, auction_id_value, user_id_field, user_id_value)
        redis.call("XADD", "bids:vinteage", "MAXLEN", "~", 1000, "*", bid_field, bid_value, auction_id_field, auction_id_value, user_id_field, user_id_value)
        return "OK"
    end

    local current_bid = tonumber(current_high)
    local min_bid = current_bid + 1
    local max_bid = current_bid + 100

    if bid_value < min_bid or bid_value > max_bid then
        return redis.error_reply("Error: bid amount not acceptable")
    end

    redis.call("HSET", bid_key, bid_field, bid_value, auction_id_field, auction_id_value, user_id_field, user_id_value)
    redis.call("XADD", "bids:vinteage", "MAXLEN", "~", 1000, "*", bid_field, bid_value, auction_id_field, auction_id_value, user_id_field, user_id_value)
    return "OK"
"""


class BidEnqueue:
    _CURRENT_HIGHEST_BID_FIELD = "current_highest"
    _AUCTION_ID_FIELD = "auction_id"
    _USER_ID_FIELD = "user_id"

    def __init__(self, redis: RedisClient | None = None, add_bid_script: str | None = None):
        self._redis = redis or get_redis_client()
        self._place_bid_script = self._redis._client.register_script(add_bid_script or ADD_BID_SCRIPT)

    async def publish_bid(self, bid_payload: CreateAuctionBid):
        bid_key = BID_KEY.format(auction_id=bid_payload.auction_id)
        await self._place_bid_script(
            keys=[bid_key, self._CURRENT_HIGHEST_BID_FIELD, self._AUCTION_ID_FIELD, self._USER_ID_FIELD],
            args=[bid_payload.bid_amount, bid_payload.auction_id, bid_payload.user_id],
        )
        return CreateBidResponse(message="Ok")
