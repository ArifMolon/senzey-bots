"""Schemas emitted by AI analysis agents."""

from dataclasses import dataclass, field
from typing import Dict, Optional

from trading_board.schemas import TradingOrder


@dataclass
class AnalysisSignal:
    source_agent: str
    epic: str
    direction: str
    confidence: float
    size: float
    currency_code: str
    reasoning: str
    metadata: Dict = field(default_factory=dict)
    order_type: str = "MARKET"
    expiry: str = "-"
    quote_id: Optional[str] = None
    limit_distance: Optional[float] = None
    limit_level: Optional[float] = None
    stop_distance: Optional[float] = None
    stop_level: Optional[float] = None
    level: Optional[float] = None
    time_in_force: Optional[str] = None
    force_open: bool = False
    guaranteed_stop: bool = False
    trailing_stop: bool = False
    trailing_stop_increment: Optional[float] = None

    def to_order(self):
        enriched_metadata = {
            **self.metadata,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
        }

        return TradingOrder(
            source_agent=self.source_agent,
            epic=self.epic,
            direction=self.direction,
            size=self.size,
            currency_code=self.currency_code,
            order_type=self.order_type,
            expiry=self.expiry,
            force_open=self.force_open,
            guaranteed_stop=self.guaranteed_stop,
            trailing_stop=self.trailing_stop,
            quote_id=self.quote_id,
            level=self.level,
            limit_distance=self.limit_distance,
            limit_level=self.limit_level,
            stop_distance=self.stop_distance,
            stop_level=self.stop_level,
            trailing_stop_increment=self.trailing_stop_increment,
            time_in_force=self.time_in_force,
            metadata=enriched_metadata,
        )
