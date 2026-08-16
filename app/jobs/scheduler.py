from taskiq import TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource

from app.core.config import settings
from app.redis_client.client import RedisClientConfig

from .broker import broker

redis_config = RedisClientConfig(host=settings.REDIS_SERVER)
redis_url = redis_config.get_redis_url()

label_source = LabelScheduleSource(broker)


scheduler = TaskiqScheduler(broker, sources=[label_source])
