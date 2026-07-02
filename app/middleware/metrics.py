import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import get_settings
from app.observability.metrics import (
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUESTS_TOTAL,
    inc_counter,
    observe_histogram,
)
from app.utils.helpers import route_template


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        started = time.perf_counter()
        status_code = 500
        response = None

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            settings = get_settings()
            endpoint = route_template(request.scope)
            elapsed = time.perf_counter() - started
            labels = {
                "method": request.method,
                "endpoint": endpoint,
                "status": str(status_code),
                "service": settings.service_name,
            }
            inc_counter(HTTP_REQUESTS_TOTAL.labels(**labels))
            observe_histogram(HTTP_REQUEST_DURATION_SECONDS.labels(**labels), elapsed)

            if response is not None:
                response.headers["x-observed-service"] = settings.service_name
