from functools import lru_cache

from redis import Redis
from rq import Queue

from app.config import settings


@lru_cache
def get_queue() -> Queue:
    return Queue("storybook", connection=Redis.from_url(settings.redis_url))
