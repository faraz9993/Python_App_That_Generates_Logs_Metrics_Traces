from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/ready")
async def ready(request: Request) -> dict:
    downstream = await request.app.state.downstream_client.health()
    return {"status": "ready", "downstream": downstream}

