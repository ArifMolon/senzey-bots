"""Persistence adapters for trading orders and audit events."""

from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Dict, Optional

from .schemas import OrderStatus, TradingOrder


def utc_now():
    return datetime.now(timezone.utc)


class OrderStore(ABC):
    @abstractmethod
    def create_order(self, order: TradingOrder):
        raise NotImplementedError

    @abstractmethod
    def mark_executing(self, order_id: str):
        raise NotImplementedError

    @abstractmethod
    def mark_filled(self, order_id: str, deal_reference: Optional[str]):
        raise NotImplementedError

    @abstractmethod
    def mark_rejected(self, order_id: str, error_message: str):
        raise NotImplementedError


class InMemoryOrderStore(OrderStore):
    """Simple store for local tests and dry-run development."""

    def __init__(self):
        self.orders: Dict[str, Dict] = {}
        self.events = []

    def create_order(self, order):
        self.orders[order.order_id] = {
            "order_id": order.order_id,
            "payload": order.to_payload(),
            "status": OrderStatus.PENDING.value,
            "deal_reference": None,
            "error_message": None,
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "executed_at": None,
        }
        self.events.append(
            {
                "order_id": order.order_id,
                "event_type": "order_created",
                "event_data": order.to_payload(),
                "created_at": utc_now(),
            }
        )

    def mark_executing(self, order_id):
        order = self.orders[order_id]
        order["status"] = OrderStatus.EXECUTING.value
        order["updated_at"] = utc_now()
        self.events.append(
            {
                "order_id": order_id,
                "event_type": "order_executing",
                "event_data": {},
                "created_at": utc_now(),
            }
        )

    def mark_filled(self, order_id, deal_reference):
        order = self.orders[order_id]
        order["status"] = OrderStatus.FILLED.value
        order["deal_reference"] = deal_reference
        order["updated_at"] = utc_now()
        order["executed_at"] = utc_now()
        self.events.append(
            {
                "order_id": order_id,
                "event_type": "order_filled",
                "event_data": {"deal_reference": deal_reference},
                "created_at": utc_now(),
            }
        )

    def mark_rejected(self, order_id, error_message):
        order = self.orders[order_id]
        order["status"] = OrderStatus.REJECTED.value
        order["error_message"] = error_message
        order["updated_at"] = utc_now()
        self.events.append(
            {
                "order_id": order_id,
                "event_type": "order_rejected",
                "event_data": {"error_message": error_message},
                "created_at": utc_now(),
            }
        )


class PostgresOrderStore(OrderStore):
    """PostgreSQL store with event-sourcing style audit trail."""

    def __init__(self, dsn: str, create_tables_on_boot=True):
        try:
            import psycopg2  # type: ignore
            from psycopg2.extras import Json  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "psycopg2 is required for PostgresOrderStore. "
                "Install with `pip install psycopg2-binary`."
            ) from exc

        self._psycopg2 = psycopg2
        self._json = Json
        self._dsn = dsn
        if create_tables_on_boot:
            self.ensure_schema()

    @contextmanager
    def _connection(self):
        conn = self._psycopg2.connect(self._dsn)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def ensure_schema(self):
        with self._connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS orders (
                        order_id TEXT PRIMARY KEY,
                        source_agent TEXT NOT NULL,
                        epic TEXT NOT NULL,
                        direction TEXT NOT NULL,
                        size NUMERIC NOT NULL,
                        currency_code TEXT NOT NULL,
                        status TEXT NOT NULL,
                        payload JSONB NOT NULL,
                        deal_reference TEXT NULL,
                        error_message TEXT NULL,
                        created_at TIMESTAMPTZ NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL,
                        executed_at TIMESTAMPTZ NULL
                    );
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS order_events (
                        event_id BIGSERIAL PRIMARY KEY,
                        order_id TEXT NOT NULL REFERENCES orders(order_id),
                        event_type TEXT NOT NULL,
                        event_data JSONB NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL
                    );
                    """
                )

    def _append_event(self, cursor, order_id, event_type, event_data):
        cursor.execute(
            """
            INSERT INTO order_events (order_id, event_type, event_data, created_at)
            VALUES (%s, %s, %s, %s)
            """,
            (order_id, event_type, self._json(event_data), utc_now()),
        )

    def create_order(self, order):
        payload = order.to_payload()
        with self._connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO orders (
                        order_id, source_agent, epic, direction, size, currency_code,
                        status, payload, deal_reference, error_message,
                        created_at, updated_at, executed_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        order.order_id,
                        order.source_agent,
                        order.epic,
                        order.direction,
                        order.size,
                        order.currency_code,
                        OrderStatus.PENDING.value,
                        self._json(payload),
                        None,
                        None,
                        utc_now(),
                        utc_now(),
                        None,
                    ),
                )
                self._append_event(cursor, order.order_id, "order_created", payload)

    def mark_executing(self, order_id):
        with self._connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE orders
                    SET status=%s, updated_at=%s
                    WHERE order_id=%s
                    """,
                    (OrderStatus.EXECUTING.value, utc_now(), order_id),
                )
                self._append_event(cursor, order_id, "order_executing", {})

    def mark_filled(self, order_id, deal_reference):
        with self._connection() as conn:
            with conn.cursor() as cursor:
                now = utc_now()
                cursor.execute(
                    """
                    UPDATE orders
                    SET status=%s, deal_reference=%s, updated_at=%s, executed_at=%s
                    WHERE order_id=%s
                    """,
                    (OrderStatus.FILLED.value, deal_reference, now, now, order_id),
                )
                self._append_event(
                    cursor,
                    order_id,
                    "order_filled",
                    {"deal_reference": deal_reference},
                )

    def mark_rejected(self, order_id, error_message):
        with self._connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE orders
                    SET status=%s, error_message=%s, updated_at=%s
                    WHERE order_id=%s
                    """,
                    (OrderStatus.REJECTED.value, error_message, utc_now(), order_id),
                )
                self._append_event(
                    cursor,
                    order_id,
                    "order_rejected",
                    {"error_message": error_message},
                )
