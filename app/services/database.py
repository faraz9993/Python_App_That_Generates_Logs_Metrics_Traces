import json
from datetime import datetime

import asyncpg
from opentelemetry.trace import SpanKind, Status, StatusCode

from app.config import Settings
from app.observability.logging import get_logger
from app.observability.metrics import DB_CALLS_TOTAL, inc_counter
from app.observability.tracing import get_tracer

logger = get_logger("database")
tracer = get_tracer(__name__)

CREATE_ORDERS_TABLE = """
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    items JSONB NOT NULL,
    total NUMERIC(10, 2) NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);
"""

INSERT_ORDER = """
INSERT INTO orders (id, customer_id, items, total, status, created_at)
VALUES ($1, $2, $3, $4, $5, $6)
ON CONFLICT (id) DO UPDATE SET
    customer_id = EXCLUDED.customer_id,
    items = EXCLUDED.items,
    total = EXCLUDED.total,
    status = EXCLUDED.status;
"""


class Database:
    """Thin async Postgres wrapper. Failures are logged and swallowed so the
    in-memory API keeps working even if the database pod is unreachable."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._pool: asyncpg.Pool | None = None

    @property
    def available(self) -> bool:
        return self._pool is not None

    async def connect(self) -> None:
        with tracer.start_as_current_span("db.connect", kind=SpanKind.CLIENT) as span:
            span.set_attribute("db.system", "postgresql")
            span.set_attribute("db.name", self.settings.db_name)
            span.set_attribute("net.peer.name", self.settings.db_host)
            span.set_attribute("net.peer.port", self.settings.db_port)
            try:
                self._pool = await asyncpg.create_pool(
                    host=self.settings.db_host,
                    port=self.settings.db_port,
                    user=self.settings.db_user,
                    password=self.settings.db_password,
                    database=self.settings.db_name,
                    min_size=self.settings.db_pool_min_size,
                    max_size=self.settings.db_pool_max_size,
                    timeout=self.settings.db_connect_timeout_seconds,
                )
                async with self._pool.acquire() as conn:
                    await conn.execute(CREATE_ORDERS_TABLE)
                logger.info(
                    "database connected",
                    host=self.settings.db_host,
                    port=self.settings.db_port,
                    db=self.settings.db_name,
                )
            except Exception as exc:  # noqa: BLE001 - degrade gracefully
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, str(exc)))
                span.set_attribute("db.connect_failed", True)
                logger.error(
                    "database connection failed",
                    host=self.settings.db_host,
                    port=self.settings.db_port,
                    error=str(exc),
                )
                self._pool = None

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def insert_order(self, order) -> bool:
        """Persist an order to Postgres. Returns True on success."""
        if self._pool is None:
            logger.warning("database unavailable, skipping persist", order_id=order.id)
            return False

        with tracer.start_as_current_span("db.orders.insert", kind=SpanKind.CLIENT) as span:
            span.set_attribute("db.system", "postgresql")
            span.set_attribute("db.name", self.settings.db_name)
            span.set_attribute("db.operation", "INSERT")
            span.set_attribute("db.sql.table", "orders")
            span.set_attribute("net.peer.name", self.settings.db_host)
            span.set_attribute("net.peer.port", self.settings.db_port)
            span.set_attribute("db.statement", INSERT_ORDER.strip())
            span.set_attribute("order.id", order.id)
            try:
                items_json = json.dumps([item.model_dump() for item in order.items])
                created_at: datetime = order.created_at
                async with self._pool.acquire() as conn:
                    await conn.execute(
                        INSERT_ORDER,
                        order.id,
                        order.customer_id,
                        items_json,
                        order.total,
                        order.status.value,
                        created_at,
                    )
                inc_counter(
                    DB_CALLS_TOTAL.labels(
                        service=self.settings.service_name,
                        operation="insert_order",
                        status="success",
                    )
                )
                logger.info("order persisted to database", order_id=order.id)
                return True
            except Exception as exc:  # noqa: BLE001 - degrade gracefully
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, str(exc)))
                inc_counter(
                    DB_CALLS_TOTAL.labels(
                        service=self.settings.service_name,
                        operation="insert_order",
                        status="error",
                    )
                )
                logger.error("order persist failed", order_id=order.id, error=str(exc))
                return False
