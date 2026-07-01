from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import get_settings
from app.observability.tracing import get_tracer


class BusinessTracingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        settings = get_settings()
        if not settings.nested_spans_enabled:
            return await call_next(request)

        tracer = get_tracer(__name__)
        with tracer.start_as_current_span("request.business_context") as span:
            span.set_attribute("http.route_hint", request.url.path)
            span.set_attribute("feature.nested_spans_enabled", settings.nested_spans_enabled)
            return await call_next(request)

