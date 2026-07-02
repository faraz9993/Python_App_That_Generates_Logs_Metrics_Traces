import httpx

from app.config import Settings
from app.observability.logging import get_logger
from app.observability.metrics import DOWNSTREAM_CALLS_TOTAL
from app.observability.metrics import inc_counter
from app.observability.tracing import get_tracer


class DownstreamClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client = httpx.AsyncClient(base_url=settings.downstream_service_url, timeout=2.0)
        self._logger = get_logger("downstream")
        self._tracer = get_tracer(__name__)

    async def health(self) -> dict:
        with self._tracer.start_as_current_span("downstream.health") as span:
            span.set_attribute("peer.service", self.settings.downstream_service_url)
            try:
                response = await self._client.get("/health")
                inc_counter(
                    DOWNSTREAM_CALLS_TOTAL.labels(
                        service=self.settings.service_name,
                        target=self.settings.downstream_service_url,
                        status=str(response.status_code),
                    )
                )
                return {"status_code": response.status_code, "reachable": response.is_success}
            except httpx.HTTPError as exc:
                inc_counter(
                    DOWNSTREAM_CALLS_TOTAL.labels(
                        service=self.settings.service_name,
                        target=self.settings.downstream_service_url,
                        status="error",
                    )
                )
                self._logger.error("downstream call failed", error=str(exc))
                span.record_exception(exc)
                return {"status_code": None, "reachable": False, "error": str(exc)}

    async def close(self) -> None:
        await self._client.aclose()
