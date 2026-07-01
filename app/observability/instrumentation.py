from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

from app.config import Settings


def instrument_app(app: FastAPI, settings: Settings) -> None:
    if not settings.otel_enabled:
        return
    FastAPIInstrumentor.instrument_app(app)
    HTTPXClientInstrumentor().instrument()

