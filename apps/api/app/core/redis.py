from redis.asyncio import Redis, from_url

from app.core.config import settings

redis_client: Redis | None = None


async def connect_redis() -> Redis:
    global redis_client
    redis_client = from_url(settings.redis_url, decode_responses=True, health_check_interval=30)
    await redis_client.ping()
    return redis_client


async def close_redis() -> None:
    global redis_client
    if redis_client is not None:
        await redis_client.aclose()
        redis_client = None


def get_redis() -> Redis:
    if redis_client is None:
        raise RuntimeError("Redis is not connected")
    return redis_client
