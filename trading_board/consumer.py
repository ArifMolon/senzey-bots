"""Order consumer that executes orders with trading_ig."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from .schemas import TradingOrder

logger = logging.getLogger(__name__)


class TradingBoardConsumer:
    def __init__(self, subscriber, store, execution_service):
        self.subscriber = subscriber
        self.store = store
        self.execution_service = execution_service

    def _extract_deal_reference(self, response: Any) -> Optional[str]:
        if isinstance(response, dict):
            if "dealReference" in response:
                return response["dealReference"]
            if "deal_reference" in response:
                return response["deal_reference"]
            deal_status = response.get("dealStatus") or response.get("deal_status")
            if isinstance(deal_status, dict):
                return deal_status.get("dealReference") or deal_status.get(
                    "deal_reference"
                )
        return None

    def _execute_with_ig(self, order: TradingOrder):
        return self.execution_service.create_open_position(
            currency_code=order.currency_code,
            direction=order.direction,
            epic=order.epic,
            expiry=order.expiry,
            force_open=order.force_open,
            guaranteed_stop=order.guaranteed_stop,
            level=order.level,
            limit_distance=order.limit_distance,
            limit_level=order.limit_level,
            order_type=order.order_type,
            quote_id=order.quote_id,
            size=order.size,
            stop_distance=order.stop_distance,
            stop_level=order.stop_level,
            trailing_stop=order.trailing_stop,
            trailing_stop_increment=order.trailing_stop_increment,
            time_in_force=order.time_in_force,
        )

    def process_payload(self, payload: Dict[str, Any]):
        order = TradingOrder.from_payload(payload)
        order.validate()
        self.store.create_order(order)
        self.store.mark_executing(order.order_id)

        try:
            response = self._execute_with_ig(order)
            deal_reference = self._extract_deal_reference(response)
            self.store.mark_filled(order.order_id, deal_reference)
            return {"order_id": order.order_id, "status": "filled"}
        except Exception as exc:
            self.store.mark_rejected(order.order_id, str(exc))
            logger.exception("Order execution failed for %s", order.order_id)
            return {"order_id": order.order_id, "status": "rejected", "error": str(exc)}

    def run_forever(self):
        for payload in self.subscriber.listen():
            self.process_payload(payload)
