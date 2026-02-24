"""Publisher bridge from analysis signals to trading board orders."""

from trading_board.redis_client import RedisOrderPublisher

from .schemas import AnalysisSignal


class AnalysisOrderPublisher:
    def __init__(self, redis_url: str, redis_channel: str):
        self.publisher = RedisOrderPublisher(redis_url, redis_channel)

    def publish_signal(self, signal: AnalysisSignal):
        order = signal.to_order()
        order.validate()
        return self.publisher.publish(order)
