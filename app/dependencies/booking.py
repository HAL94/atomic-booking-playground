import json
import logging
from typing import Annotated, Optional
from uuid import UUID

from fastapi import Header, Request, Response

from app.core.exceptions import InternalFailureException
from app.dependencies.auth import CurrentUser
from app.dependencies.idempotency import IdempotencyChecker, RedisTypeKey
from app.dependencies.redis import get_redis_client
from app.domain.booking import BookingBase

logger = logging.getLogger("uvicorn")

BookingIdempotencyHeader = Annotated[str, Header(alias="Idempotency-Key")]


class BookingIdempotency:
    _key_prefix = "booking_idempotency:"
    _lock_timeout_seconds = 10
    _cache_ttl_seconds = 60

    def __init__(self):
        self._checker = IdempotencyChecker(self._lock_timeout_seconds, self._cache_ttl_seconds)

    async def __call__(
        self,
        request: Request,
        response: Response,
        user: CurrentUser,
        seat_id: UUID,
        idempotency_key: BookingIdempotencyHeader,
    ) -> Optional[BookingBase]:
        logger.info(f"[BookingIdempotency]: idempotency-key {idempotency_key}")

        redis_cache_key = self._checker.build_redis_key(
            RedisTypeKey.CACHE, self._key_prefix, idempotency_key, str(seat_id), str(user.id)
        )
        redis_lock_key = self._checker.build_redis_key(
            RedisTypeKey.LOCK, self._key_prefix, idempotency_key, str(seat_id), str(user.id)
        )

        result = await self._checker.check_idempotency(
            request=request,
            response=response,
            redis_cache_key=redis_cache_key,
            redis_lock_key=redis_lock_key,
            idempotency_key=idempotency_key,
        )

        try:
            if result:
                return BookingBase.model_validate(result, from_attributes=True)
        except Exception as e:
            logger.exception(f"[BookingIdempotency]: failed to validate BookingBase payload {str(e)}")
            raise InternalFailureException("Cached idempotency payload failed validation.")

        return None

    @classmethod
    async def clear_booking_cache_lock(
        cls, redis_lock_key: Optional[str] = None, lock_token: Optional[str] = None
    ) -> bool:
        """
        Given an idempotency key with a user id, clear the booking cache lock
        """
        if not redis_lock_key or not lock_token:
            return False
        RELEASE_LOCK_SCRIPT = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
        """
        try:
            redis = get_redis_client()
            await redis._client.eval(RELEASE_LOCK_SCRIPT, 1, redis_lock_key, lock_token)
            return True
        except Exception as e:
            logger.exception(f"[BookingIdempotency]: failed to clear locked booking {str(e)}")
            return False

    @classmethod
    async def cache_booking_response(
        cls, cache_key: str, booking: BookingBase, status_code: Optional[int] = 202
    ) -> bool:
        """
        Given a booking, cache it base on the configuration (key_prefix, cache_ttl_seconds)
        """
        try:
            # Step 1: prepare JSON cache
            booking_json = booking.model_dump(mode="json")
            cached_booking_json = json.dumps({"body": booking_json, "status_code": status_code})

            # Step 2: get redis client
            redis = get_redis_client()
            await redis.set(cache_key, cached_booking_json, ex=cls._cache_ttl_seconds)
            return True

        except Exception as e:
            logger.exception(f"[BookingIdempotency]: failed to cache booking {str(e)}")
            raise e
