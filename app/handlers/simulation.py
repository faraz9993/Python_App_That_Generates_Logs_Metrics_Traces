import asyncio
import random

from fastapi import APIRouter, HTTPException, Request

from app.config import get_settings
from app.observability.logging import get_logger
from app.observability.tracing import get_tracer

router = APIRouter(prefix="/simulate", tags=["simulation"])
settings = get_settings()
tracer = get_tracer(__name__)
logger = get_logger("simulation")


@router.get("/normal")
async def simulate_normal(request: Request) -> dict:
    with tracer.start_as_current_span("simulation.normal"):
        downstream = await request.app.state.downstream_client.health()
        logger.info("normal simulation completed", downstream_reachable=downstream["reachable"])
        return {"mode": "normal", "downstream": downstream}


@router.get("/error")
async def simulate_error() -> dict:
    with tracer.start_as_current_span("simulation.error") as span:
        exc = RuntimeError("intentional simulation error")
        if settings.error_spans_enabled:
            span.record_exception(exc)
            span.set_attribute("error.simulated", True)
        logger.error("intentional simulation error", error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/latency")
async def simulate_latency() -> dict:
    latency = random.uniform(0.25, 1.75)
    with tracer.start_as_current_span("simulation.latency") as span:
        span.set_attribute("latency.seconds", latency)
        await asyncio.sleep(latency)
        logger.info("latency simulation completed", latency_ms=round(latency * 1000, 2))
        return {"mode": "latency", "latency_seconds": round(latency, 3)}


@router.get("/cpu")
async def simulate_cpu() -> dict:
    if not settings.cpu_simulation_enabled:
        return {"mode": "cpu", "enabled": False}
    with tracer.start_as_current_span("simulation.cpu") as span:
        total = sum(i * i for i in range(250_000))
        span.set_attribute("work.units", 250_000)
        return {"mode": "cpu", "enabled": True, "checksum": total % 10_000}


@router.get("/memory")
async def simulate_memory() -> dict:
    if not settings.memory_simulation_enabled:
        return {"mode": "memory", "enabled": False}
    with tracer.start_as_current_span("simulation.memory") as span:
        payload = ["observability"] * 100_000
        span.set_attribute("memory.items", len(payload))
        return {"mode": "memory", "enabled": True, "items_allocated": len(payload)}

