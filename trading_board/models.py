"""Lightweight model constants for trading board persistence."""

ORDERS_TABLE = "orders"
ORDER_EVENTS_TABLE = "order_events"

ORDER_COLUMNS = (
    "order_id",
    "source_agent",
    "epic",
    "direction",
    "size",
    "currency_code",
    "status",
    "payload",
    "deal_reference",
    "error_message",
    "created_at",
    "updated_at",
    "executed_at",
)

ORDER_EVENT_COLUMNS = (
    "event_id",
    "order_id",
    "event_type",
    "event_data",
    "created_at",
)
