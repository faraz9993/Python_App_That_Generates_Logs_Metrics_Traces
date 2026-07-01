import asyncio
import random
from collections.abc import Awaitable, Callable

import httpx

from app.config import Settings
from app.observability.logging import get_logger


class TrafficGenerator:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self._logger = get_logger("traffic_generator")
        self._routes: list[tuple[str, str, Callable[[], dict | None]]] = [
            ("GET", "/health", lambda: None),
            ("GET", "/api/orders", lambda: None),
            ("GET", "/api/customers", lambda: None),
            ("GET", "/api/products", lambda: None),
            ("GET", "/simulate/normal", lambda: None),
            ("GET", "/simulate/latency", lambda: None),
            (
                "POST",
                "/api/orders",
                lambda: {
                    "customer_id": random.choice([1, 2, 3]),
                    "items": [{"product_id": random.choice([1, 2, 3]), "quantity": 1}],
                },
            ),
        ]

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._stop_event.clear()
            self._task = asyncio.create_task(self._run(), name="traffic-generator")

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task:
            await self._task

    async def _run(self) -> None:
        await asyncio.sleep(1.0)
        interval = 1 / self.settings.traffic_rate
        async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{self.settings.port}") as client:
            while not self._stop_event.is_set():
                method, path, body_factory = self._choose_route()
                try:
                    if random.random() < self.settings.latency_rate:
                        path = "/simulate/latency"
                    if random.random() < self.settings.error_rate:
                        path = "/simulate/error"
                        method = "GET"
                        body_factory = lambda: None

                    response = await client.request(method, path, json=body_factory())
                    self._logger.debug(
                        "synthetic request completed",
                        method=method,
                        path=path,
                        status=response.status_code,
                    )
                except Exception as exc:
                    self._logger.error("synthetic request failed", error=str(exc))
                await self._sleep(interval)

    def _choose_route(self) -> tuple[str, str, Callable[[], dict | None]]:
        return random.choice(self._routes)

    async def _sleep(self, interval: float) -> None:
        try:
            await asyncio.wait_for(self._stop_event.wait(), timeout=interval)
        except TimeoutError:
            return

