import json
import logging
import traceback
from typing import Any, Optional, Union

import redis.asyncio as redis
from pydantic import BaseModel, Field

logger = logging.getLogger("uvicorn")
logger.setLevel(logging.INFO)


class RedisClientConfig(BaseModel):
    host: Optional[str] = Field(default="localhost")
    password: Optional[str] = Field(default=None)
    db: Optional[int] = Field(default=0)
    port: Optional[int] = Field(default=6379)
    decode_responses: Optional[bool] = Field(default=True)
    max_connections: Optional[int] = Field(default=50)

    def get_redis_url(self) -> str:
        """Return a Redis connection URL built from this configuration."""
        host = self.host or "localhost"
        port = self.port or 6379
        db = self.db or 0
        if self.password:
            return f"redis://:{self.password}@{host}:{port}/{db}"
        return f"redis://{host}:{port}/{db}"


class RedisClient:
    def __init__(self, redis_config: RedisClientConfig):
        """Initial Async Redis client
        Args:
            - redis_config: Configuration Connection for Redis instance
                - host: Redis server host
                - port: Redis server port
                - db: Redis database number
                - password: Redis password (if required)
                - decode_responses: Whether to decode responses to strings
                - max_connections: Maximum number of connections in the pool
        """
        self._config = redis_config
        self._client: Optional[redis.Redis] = None
        self._pool = redis.ConnectionPool.from_url(
            self._config.get_redis_url(), max_connections=self._config.max_connections, retry_on_timeout=True
        )

    async def connect(self) -> bool:
        """Connect to the redis instance"""
        try:
            if not self._client:
                self._client = redis.Redis(connection_pool=self._pool)
            is_connected = await self._client.ping()
            if is_connected:
                logger.info("[RedisClient] is connected successfully!")
            return is_connected
        except Exception as e:
            logger.error(f"An error occured while connecting: {e} {traceback.format_exc()}")
            return False

    async def disconnect(self):
        """Disconnect the redis client"""
        try:
            await self.disconnect()
        except Exception as e:
            logger.error(f"An error occured disconnecting: {e} {traceback.format_exc()}")

    @property
    def client(self) -> redis.Redis:
        """Get the Redis client instance."""
        if self._client is None:
            raise RuntimeError("Redis client not connected. Call connect() first.")
        return self._client

    # Key-Value Operations
    async def set(
        self,
        key: str,
        value: Any,
        /,
        *,
        ex: Optional[int] = None,
        px: Optional[int] = None,
        nx: bool = False,
        xx: bool = False,
    ) -> bool:
        """
        Set a key-value pair.

        Args:
            key: The key to set
            value: The value to set (will be JSON-serialized if not a string)
            ex: Expiration time in seconds
            px: Expiration time in milliseconds
            nx: Only set if key doesn't exist
            xx: Only set if key exists

        Returns:
            True if successful, False otherwise
        """
        try:
            if not isinstance(value, (str, bytes)):
                value = json.dumps(value)

            result = await self.client.set(key, value, ex=ex, px=px, nx=nx, xx=xx)
            return bool(result)
        except Exception as e:
            logger.error(f"[RedisClient]: Failed to set key: {key} with value: {value}. Error: {e}")
            return False

    async def get(self, key: str, /, *, as_json: bool = False) -> Optional[Union[str, Any]]:
        """
        Get a value by key.

        Args:
            key: The key to retrieve
            as_json: Whether to parse the value as JSON

        Returns:
            The value or None if key doesn't exist
        """
        value = await self.client.get(key)
        if value is None:
            return None

        if as_json:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value

        return value

    async def delete(self, *keys: str) -> int:
        """
        Delete one or more keys.

        Args:
            keys: Keys to delete

        Returns:
            Number of keys deleted
        """
        return await self.client.delete(*keys)

    async def exists(self, *keys: str) -> int:
        """
        Check if keys exist.

        Args:
            keys: Keys to check

        Returns:
            Number of existing keys
        """
        return await self.client.exists(*keys)
