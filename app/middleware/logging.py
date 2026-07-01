import time
import uuid

import structlog.contextvars
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.observability.logging import get_logger
from app.utils.helpers import route_template


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        structlog.contextvars.bind_contextvars(request_id=request_id)
        started = time.perf_counter()
        status_code = 500
        logger = get_logger("request")

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception:
            logger.exception(
                "request failed",
                method=request.method,
                path=request.url.path,
                query_params=dict(request.query_params),
                client_ip=request.client.host if request.client else "",
                request_id=request_id,
            )
            raise
        finally:
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.info(
                "request completed",
                method=request.method,
                path=request.url.path,
                endpoint=route_template(request.scope),
                query_params=dict(request.query_params),
                status=status_code,
                client_ip=request.client.host if request.client else "",
                latency_ms=latency_ms,
                request_id=request_id,
            )
            structlog.contextvars.clear_contextvars()

