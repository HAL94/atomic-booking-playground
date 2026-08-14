from typing import Annotated

from fastapi import Depends

from app.core.config import settings
from app.redis_client.client import RedisClient, RedisClientConfig

redis_client: RedisClient | None = None
redis_config: RedisClientConfig = RedisClientConfig(host=settings.REDIS_SERVER)

def get_redis_client() -> RedisClient:
    global redis_client  # noqa: PLW0603, W291
    if not redis_client:
        redis_client = RedisClient(redis_config)
    return redis_client


ARedisClient = Annotated[RedisClient, Depends(get_redis_client)]
