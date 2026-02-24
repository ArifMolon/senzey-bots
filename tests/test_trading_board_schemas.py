from trading_board.schemas import OrderStatus, TradingOrder


class TestTradingBoardSchemas:
    def test_roundtrip_payload(self):
        order = TradingOrder(
            source_agent="analysis-agent-1",
            epic="IX.D.ASX.IFM.IP",
            direction="BUY",
            size=1.2,
            currency_code="AUD",
            metadata={"reasoning": "momentum breakout"},
        )
        order.validate()

        payload = order.to_payload()
        reconstructed = TradingOrder.from_payload(payload)

        assert reconstructed.order_id == order.order_id
        assert reconstructed.epic == "IX.D.ASX.IFM.IP"
        assert reconstructed.status == OrderStatus.PENDING
        assert reconstructed.metadata["reasoning"] == "momentum breakout"

    def test_invalid_direction_raises(self):
        order = TradingOrder(
            source_agent="analysis-agent-1",
            epic="IX.D.ASX.IFM.IP",
            direction="HOLD",
            size=0.5,
            currency_code="AUD",
        )

        try:
            order.validate()
            assert False, "Expected ValueError"
        except ValueError as exc:
            assert "direction" in str(exc)
