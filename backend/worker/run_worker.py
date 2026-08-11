import logging
import sys

from redis import Redis
from rq import Queue, SimpleWorker, Worker

from app.config import settings


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    connection = Redis.from_url(settings.redis_url)
    queue = Queue("storybook", connection=connection)
    worker_class = SimpleWorker if sys.platform == "win32" else Worker
    worker = worker_class([queue], connection=connection)
    worker.work()


if __name__ == "__main__":
    main()
