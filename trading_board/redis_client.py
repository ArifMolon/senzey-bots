"""Redis Pub/Sub transport for trading orders."""

import json
from typing import Generator

from .schemas import TradingOrder


class RedisOrderPublisher:
    def __init__(self, redis_url: str, channel: str):
        self.channel = channel
        try:
            import redis  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "redis package is required for RedisOrderPublisher. "
                "Install with `pip install redis`."
            ) from exc
        self._redis = redis.Redis.from_url(redis_url)

    def publish(self, order: TradingOrder):
        order.validate()
        return self._redis.publish(self.channel, json.dumps(order.to_payload()))


class RedisOrderSubscriber:
    def __init__(self, redis_url: str, channel: str):
        self.channel = channel
        try:
            import redis  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "redis package is required for RedisOrderSubscriber. "
                "Install with `pip install redis`."
            ) from exc
        self._redis = redis.Redis.from_url(redis_url)

    def listen(self) -> Generator[dict, None, None]:
        pubsub = self._redis.pubsub(ignore_subscribe_messages=True)
        pubsub.subscribe(self.channel)
        for message in pubsub.listen():
            raw_data = message["data"]
            if isinstance(raw_data, bytes):
                raw_data = raw_data.decode("utf-8")
            yield json.loads(raw_data)
