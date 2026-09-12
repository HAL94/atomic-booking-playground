from pydantic import BaseModel

from app.dependencies.redis import get_redis_client
from app.redis_client.client import RedisClient

ADD_BID_SCRIPT = """
    -- HASH key
    local bid_key = KEYS[1]
    -- Fields
    local bid_field = KEYS[2]
    local auction_id_field = KEYS[3]
    local user_id_field = KEYS[4]
    -- Values
    local auction_id_value = ARGV[1]
    local user_id_value = ARGV[2]

    local bid_value = redis.call("HGET", bid_key, bid_field)
    if not bid_value then
        bid_value = math.random(10, 15)
        redis.call("HSET", bid_key, bid_field, bid_value, auction_id_field, auction_id_value, user_id_field, user_id_value)
        redis.call("XADD", "bids:vinteage", "MAXLEN", "~", 1000, "*", bid_field, bid_value, auction_id_field, auction_id_value, user_id_field, user_id_value)
    end

    local current_bid = bid_value + math.random(10, 50)
    redis.call("HSET", bid_key, bid_field, current_bid, auction_id_field, auction_id_value, user_id_field, user_id_value)
    redis.call("XADD", "bids:vinteage", "MAXLEN", "~", 1000, "*", bid_field, current_bid, auction_id_field, auction_id_value, user_id_field, user_id_value)
    return "OK"
"""


class CreateAuctionBid(BaseModel):
    auction_id: str
    user_id: str


BID_KEY = "bids:{auction_id}"


class TestingBidEnqueue:
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
            args=[bid_payload.auction_id, bid_payload.user_id],
        )
        return "OK"
