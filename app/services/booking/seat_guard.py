import logging
from uuid import UUID

from app.dependencies.redis import get_redis_client

logger = logging.getLogger("uvicorn")


class SeatHoldGuard:
    _reserve_key_prefix = "booking_hold"

    def __init__(self, ttl_seconds: int = 60):
        self._redis = get_redis_client()
        self.ttl_seconds = ttl_seconds  # 1 minute for testing

    def _build_key(self, seat_id: UUID) -> str:
        return f"{self._reserve_key_prefix}:{str(seat_id)}"

    async def acquire_hold(self, seat_id: UUID, user_id: UUID) -> bool:
        """Atomically set key if not exists (SET NX EX)."""
        hold_key = self._build_key(seat_id)
        try:
            acquired = await self._redis.set(hold_key, str(user_id), nx=True, ex=self.ttl_seconds)
            return bool(acquired)
        except Exception as e:
            logger.exception(f"[SeatHoldGuard] Redis error while acquiring hold for seat {seat_id}: {e}")
            raise

    async def release_hold(self, seat_id: UUID) -> bool:
        """Safely delete the seat hold key."""
        key = self._build_key(seat_id)
        try:
            await self._redis.delete(key)
            return True
        except Exception as e:
            logger.warning(f"[SeatHoldGuard] Failed to release hold for seat {seat_id}: {e}")
            return False
