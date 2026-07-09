from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from prometheus_client import REGISTRY
from prometheus_client.openmetrics.exposition import CONTENT_TYPE_LATEST, generate_latest

from app.config import get_settings
from app.handlers import business, frontend, health, simulation
from app.middleware.logging import RequestLoggingMiddleware
from app.middleware.metrics import MetricsMiddleware
from app.middleware.tracing import BusinessTracingMiddleware
from app.observability.instrumentation import instrument_app
from app.observability.logging import configure_logging, get_logger
from app.observability.tracing import configure_tracing
from app.services.database import Database
from app.services.downstream_client import DownstreamClient
from app.services.traffic_generator import TrafficGenerator

settings = get_settings()
configure_logging(settings)
configure_tracing(settings)
logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.downstream_client = DownstreamClient(settings)
    app.state.db = Database(settings)
    if settings.db_spans_enabled:
        await app.state.db.connect()
    app.state.traffic_generator = TrafficGenerator(settings)
    if settings.enable_traffic_generator:
        app.state.traffic_generator.start()
        logger.info("traffic generator started", rate=settings.traffic_rate)
    logger.info("service started")
    try:
        yield
    finally:
        if settings.enable_traffic_generator:
            await app.state.traffic_generator.stop()
            logger.info("traffic generator stopped")
        await app.state.db.close()
        await app.state.downstream_client.close()
        logger.info("service stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title="My Observability Service",
        version="0.1.0",
        description="FastAPI microservice with metrics, tracing, structured logs, and traffic simulation.",
        lifespan=lifespan,
    )
    instrument_app(app, settings)

    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(BusinessTracingMiddleware)

    app.include_router(health.router)
    app.include_router(business.router)
    app.include_router(simulation.router)
    app.include_router(frontend.router)

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(content=generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)

    return app


app = create_app()
