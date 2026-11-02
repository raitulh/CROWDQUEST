from fastapi import APIRouter
from sqlalchemy import text

from app.core.database import engine
from app.core.redis import get_redis

router = APIRouter(tags=["health"])


@router.get("/health/live")
async def liveness() -> dict:
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness() -> dict:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    await get_redis().ping()
    return {"status": "ready", "dependencies": {"database": "ok", "redis": "ok"}}
