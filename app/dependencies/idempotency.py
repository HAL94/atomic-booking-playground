import json
import logging
from enum import StrEnum
from typing import Any, Optional
from uuid import uuid4

from fastapi import HTTPException, Request, Response, status

from app.dependencies.redis import get_redis_client

logger = logging.getLogger(__name__)


class RedisTypeKey(StrEnum):
    CACHE = "cache"
    LOCK = "lock"


class IdempotencyChecker:
    def __init__(
        self,
        lock_timeout_seconds: int = 10,
        cache_ttl_seconds: int = 3600,  # 1 hour
    ):
        self.lock_timeout = lock_timeout_seconds
        self.cache_ttl = cache_ttl_seconds
        self._redis = get_redis_client()

    @classmethod
    def build_redis_key(cls, key_type: RedisTypeKey, key_prefix: str, idempotency_key: str, *keys: str) -> str:
        """
        Build a redis key in the following format:
        `{key_prefix}:{key_1}:{key_2}:{key_3}:{key_type}:{idempotency_key}`

        Args:
            - key_type: `LOCK` or `CACHE`
            - key_prefix: prefix of key
            - idempotency_key: key related for idempotency
            - *keys: any number of keys
        """
        cache_key = key_prefix

        cache_key += ":".join(keys) + ":"

        if key_type == RedisTypeKey.CACHE:
            cache_key += f"cache:{idempotency_key}"
        else:
            cache_key += f"lock:{idempotency_key}"

        return cache_key

    async def check_idempotency(
        self,
        request: Request,
        response: Response,
        redis_cache_key: str,
        redis_lock_key: str,
        idempotency_key: Optional[str],
    ) -> Optional[dict[str, Any]]:
        """
        Returns cached response dict if duplicate, or None if request should proceed.
        """
        if not idempotency_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Header 'Idempotency-Key' is required for this endpoint.",
            )

        # -------------------------------------------------------------
        # STEP 1: Fast path - Check Redis Cache
        # -------------------------------------------------------------
        cached_response = await self._redis.get(redis_cache_key)
        if cached_response:
            logger.info(f"[Idempotency] Cache HIT in Redis for key: {idempotency_key}")
            data = json.loads(cached_response)
            response.status_code = data["status_code"]
            return data["body"]

        # -------------------------------------------------------------
        # STEP 2: Acquire Distributed Lock to prevent race conditions
        # -------------------------------------------------------------
        # SET key value NX PX lock_timeout
        lock_token = str(uuid4())
        acquired_lock = await self._redis.set(redis_lock_key, lock_token, nx=True, px=int(self.lock_timeout * 1000))
        if not acquired_lock:
            logger.warning(f"[Idempotency] Concurrent request detected for key: {idempotency_key}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A request with this Idempotency-Key is currently being processed.",
            )

        # -------------------------------------------------------------
        # STEP 3: First time seeing this key -> Store context on request state
        # -------------------------------------------------------------
        request.state.idempotency_key = idempotency_key
        request.state.redis_cache_key = redis_cache_key
        request.state.redis_lock_key = redis_lock_key
        request.state.lock_token = lock_token
        return None
