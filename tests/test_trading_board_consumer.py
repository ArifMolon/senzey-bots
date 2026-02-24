from trading_board.consumer import TradingBoardConsumer
from trading_board.schemas import TradingOrder
from trading_board.store import InMemoryOrderStore


class _FakeSubscriber:
    def __init__(self, payloads):
        self._payloads = payloads

    def listen(self):
        for payload in self._payloads:
            yield payload


class _SuccessfulExecutor:
    def create_open_position(self, **kwargs):
        assert kwargs["epic"] == "IX.D.ASX.IFM.IP"
        return {"dealReference": "DIAAA111"}


class _FailingExecutor:
    def create_open_position(self, **kwargs):
        raise RuntimeError("order rejected by risk controls")


class TestTradingBoardConsumer:
    def test_process_payload_success(self):
        order = TradingOrder(
            source_agent="agent-alpha",
            epic="IX.D.ASX.IFM.IP",
            direction="BUY",
            size=1.0,
            currency_code="AUD",
        )
        store = InMemoryOrderStore()
        consumer = TradingBoardConsumer(
            subscriber=_FakeSubscriber([]),
            store=store,
            execution_service=_SuccessfulExecutor(),
        )

        result = consumer.process_payload(order.to_payload())

        assert result["status"] == "filled"
        assert store.orders[order.order_id]["status"] == "filled"
        assert store.orders[order.order_id]["deal_reference"] == "DIAAA111"

    def test_process_payload_rejection(self):
        order = TradingOrder(
            source_agent="agent-beta",
            epic="IX.D.ASX.IFM.IP",
            direction="SELL",
            size=2.5,
            currency_code="AUD",
        )
        store = InMemoryOrderStore()
        consumer = TradingBoardConsumer(
            subscriber=_FakeSubscriber([]),
            store=store,
            execution_service=_FailingExecutor(),
        )

        result = consumer.process_payload(order.to_payload())

        assert result["status"] == "rejected"
        assert "risk controls" in result["error"]
        assert store.orders[order.order_id]["status"] == "rejected"
