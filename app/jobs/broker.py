from taskiq_redis import RedisAsyncResultBackend, RedisStreamBroker

from app.core.config import settings
from app.redis_client.client import RedisClientConfig

redis_config = RedisClientConfig(host=settings.REDIS_SERVER)
redis_url = redis_config.get_redis_url()
broker = RedisStreamBroker(redis_url, queue_name="bookings_queue").with_result_backend(
    RedisAsyncResultBackend(redis_url)
)
