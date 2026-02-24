"""Data schemas for trading board order flow."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4


class OrderStatus(str, Enum):
    PENDING = "pending"
    EXECUTING = "executing"
    FILLED = "filled"
    REJECTED = "rejected"


@dataclass
class TradingOrder:
    source_agent: str
    epic: str
    direction: str
    size: float
    currency_code: str
    order_type: str = "MARKET"
    expiry: str = "-"
    force_open: bool = False
    guaranteed_stop: bool = False
    trailing_stop: bool = False
    quote_id: Optional[str] = None
    level: Optional[float] = None
    limit_distance: Optional[float] = None
    limit_level: Optional[float] = None
    stop_distance: Optional[float] = None
    stop_level: Optional[float] = None
    trailing_stop_increment: Optional[float] = None
    time_in_force: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    order_id: str = field(default_factory=lambda: str(uuid4()))
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def validate(self):
        if not self.source_agent:
            raise ValueError("source_agent is required")
        if not self.epic:
            raise ValueError("epic is required")
        if self.direction not in {"BUY", "SELL"}:
            raise ValueError("direction must be BUY or SELL")
        if self.size <= 0:
            raise ValueError("size must be greater than zero")
        if not self.currency_code:
            raise ValueError("currency_code is required")

    def to_payload(self):
        return {
            "order_id": self.order_id,
            "source_agent": self.source_agent,
            "epic": self.epic,
            "direction": self.direction,
            "size": self.size,
            "currency_code": self.currency_code,
            "order_type": self.order_type,
            "expiry": self.expiry,
            "force_open": self.force_open,
            "guaranteed_stop": self.guaranteed_stop,
            "trailing_stop": self.trailing_stop,
            "quote_id": self.quote_id,
            "level": self.level,
            "limit_distance": self.limit_distance,
            "limit_level": self.limit_level,
            "stop_distance": self.stop_distance,
            "stop_level": self.stop_level,
            "trailing_stop_increment": self.trailing_stop_increment,
            "time_in_force": self.time_in_force,
            "metadata": self.metadata,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_payload(cls, payload):
        status_value = payload.get("status", OrderStatus.PENDING.value)
        created_at_raw = payload.get("created_at")
        created_at = (
            datetime.fromisoformat(created_at_raw)
            if created_at_raw
            else datetime.now(timezone.utc)
        )

        return cls(
            order_id=payload.get("order_id", str(uuid4())),
            source_agent=payload["source_agent"],
            epic=payload["epic"],
            direction=payload["direction"],
            size=float(payload["size"]),
            currency_code=payload["currency_code"],
            order_type=payload.get("order_type", "MARKET"),
            expiry=payload.get("expiry", "-"),
            force_open=bool(payload.get("force_open", False)),
            guaranteed_stop=bool(payload.get("guaranteed_stop", False)),
            trailing_stop=bool(payload.get("trailing_stop", False)),
            quote_id=payload.get("quote_id"),
            level=payload.get("level"),
            limit_distance=payload.get("limit_distance"),
            limit_level=payload.get("limit_level"),
            stop_distance=payload.get("stop_distance"),
            stop_level=payload.get("stop_level"),
            trailing_stop_increment=payload.get("trailing_stop_increment"),
            time_in_force=payload.get("time_in_force"),
            metadata=payload.get("metadata", {}),
            status=OrderStatus(status_value),
            created_at=created_at,
        )
